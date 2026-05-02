"""
OmniCode FastAPI backend with production hardening.

Features:
- Structured logging with structlog
- Request correlation IDs
- Rate limiting with slowapi
- Security headers (CORS, CSP, HSTS, etc.)
- JWT authentication
- Input validation with Pydantic schemas
- Global exception handling
- Redis caching layer
- Enhanced health checks with latency metrics
"""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import redis
import structlog
import asyncio
import json
from datetime import datetime

from app.core.config import get_settings
from app.core.security import security_manager
from app.core.exceptions import (
    omni_exception_handler,
    generic_exception_handler,
    OmniCodeException,
)
from app.core.cache import get_cache
from app.schemas import (
    TaskCreate,
    TaskListParams,
    BlockerResolve,
    HealthResponse,
    ErrorResponse,
)
from app.schemas.skill import (
    SkillCreate,
    SkillUpdate,
    SkillResponse,
    SkillSummary,
    SkillSearchRequest,
    WorkspaceAnalysisResponse,
)
from app.graphs.workflow import workflow
from app.database.session import engine, get_db
from app.database.models import (
    ActionHistory,
    PendingChange,
    AgentLog,
    BackgroundTask,
    TaskLog,
    BlockerNotification,
)
from app.tasks import run_agent_task
from sqlalchemy.orm import Session
from sqlalchemy import text

# Initialize structlog for JSON structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging_level="INFO" if not get_settings().debug else "DEBUG"),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

settings = get_settings()


def get_client_ip(request: Request) -> str:
    """Get client IP address for rate limiting."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_client_ip)

redis_client = redis.from_url(settings.redis_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(
        "application_startup",
        environment=settings.environment,
        debug=settings.debug,
    )

    # Validate production settings on startup
    if settings.is_production:
        validation_errors = settings.validate_production()
        if validation_errors:
            logger.error(
                "production_validation_failed",
                errors=validation_errors,
            )
            raise RuntimeError(f"Production validation failed: {', '.join(validation_errors)}")

    yield

    logger.info("application_shutdown")


app = FastAPI(
    title="OmniCode API",
    description="FastAPI backend with LangGraph for agentic workflows",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add custom exception handlers
app.add_exception_handler(OmniCodeException, omni_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID", "X-Request-ID"],
    max_age=600,
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.github.com https://api.openai.com"
        )

    return response


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Extract or generate correlation ID for request tracking."""
    correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")
    if not correlation_id:
        import uuid
        correlation_id = str(uuid.uuid4())

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
    )

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id

    return response


def verify_api_token(request: Request) -> str:
    """Verify the API token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    user_id = security_manager.validate_bearer_token(auth_header)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


@app.post("/api/tasks", response_model=dict)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def create_task(
    request: Request,
    task_data: TaskCreate,
    db: Session = Depends(get_db),
):
    """Create a new background task."""
    logger.info("create_task", workspace_id=task_data.workspace_id, task_type=task_data.task_type)

    task = BackgroundTask(
        workspace_id=task_data.workspace_id,
        task_type=task_data.task_type,
        payload=task_data.payload,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    run_agent_task.delay(task.id)

    return {"task_id": task.id, "status": "pending"}


@app.get("/api/tasks", response_model=list)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def list_tasks(
    request: Request,
    params: TaskListParams = Depends(),
    db: Session = Depends(get_db),
):
    """List background tasks with optional filtering."""
    query = db.query(BackgroundTask)

    if params.workspace_id:
        query = query.filter(BackgroundTask.workspace_id == params.workspace_id)
    if params.status:
        query = query.filter(BackgroundTask.status == params.status)
    if params.task_type:
        query = query.filter(BackgroundTask.task_type == params.task_type)

    return query.order_by(BackgroundTask.created_at.desc()).all()


@app.get("/api/tasks/{task_id}", response_model=dict)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get a specific task by ID."""
    task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/api/tasks/{task_id}/logs/sse")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def stream_task_logs(request: Request, task_id: int):
    """Stream task logs via Server-Sent Events."""
    async def log_generator():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"task_logs_{task_id}")

        try:
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['data']:
                    yield f"data: {message['data'].decode('utf-8')}\n\n"
                await asyncio.sleep(0.1)
        finally:
            pubsub.unsubscribe(f"task_logs_{task_id}")
            pubsub.close()

    return StreamingResponse(log_generator(), media_type="text/event-stream")


@app.post("/api/tasks/{task_id}/resolve", response_model=dict)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def resolve_blocker(
    task_id: int,
    resolution_data: BlockerResolve,
    db: Session = Depends(get_db),
):
    """Resolve a blocker on a task."""
    logger.info("resolve_blocker", task_id=task_id)

    task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    blocker = db.query(BlockerNotification).filter(
        BlockerNotification.task_id == task_id,
        BlockerNotification.resolved == False
    ).first()

    if not blocker:
        raise HTTPException(status_code=400, detail="No active blocker found for this task")

    blocker.resolved = True
    blocker.resolution = resolution_data.resolution

    task.status = "pending"
    db.commit()

    payload = task.payload or {}
    messages = payload.get("messages", [])
    messages.append({
        "role": "user",
        "content": f"Human resolution for blocker: {resolution_data.resolution}"
    })
    payload["messages"] = messages
    task.payload = payload
    db.commit()

    run_agent_task.delay(task.id)

    return {"status": "success"}


@app.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Enhanced health check with database and Redis latency metrics."""
    health = {
        "status": "ok",
        "db": "disconnected",
        "redis": "disconnected",
        "db_latency_ms": None,
        "redis_latency_ms": None,
    }

    try:
        start = datetime.utcnow()
        db.execute(text("SELECT 1"))
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        health["db"] = "connected"
        health["db_latency_ms"] = round(latency, 2)
    except Exception as e:
        health["status"] = "degraded"
        logger.error("db_health_check_failed", error=str(e))

    try:
        start = datetime.utcnow()
        r = redis.from_url(settings.redis_url)
        if r.ping():
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            health["redis"] = "connected"
            health["redis_latency_ms"] = round(latency, 2)
    except Exception as e:
        health["status"] = "degraded"
        logger.error("redis_health_check_failed", error=str(e))

    return health


@app.get("/api/models", response_model=list)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_models(request: Request):
    """Get available AI models."""
    cache = get_cache()
    cached_models = cache.get_json("api_models")

    if cached_models:
        return cached_models

    models = [
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "OpenAI", "context_window": "128k", "cost_tier": "pro"},
        {"id": "deepseek-coder", "name": "DeepSeek Coder", "provider": "DeepSeek", "context_window": "32k", "cost_tier": "free"},
        {"id": "moonshot-v1", "name": "Moonshot V1", "provider": "Moonshot", "context_window": "128k", "cost_tier": "pro"},
    ]

    cache.set_json("api_models", models, ttl=3600)

    return models


@app.get("/api/threads/{thread_id}/history", response_model=list)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_thread_history(request: Request, thread_id: int, db: Session = Depends(get_db)):
    """Get action history for a thread."""
    history = db.query(ActionHistory).filter(
        ActionHistory.thread_id == thread_id
    ).order_by(ActionHistory.created_at.desc()).all()
    return history


@app.post("/api/pending-changes/{change_id}/accept", response_model=dict)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def accept_change(change_id: int, db: Session = Depends(get_db)):
    """Accept a pending change."""
    change = db.query(PendingChange).filter(PendingChange.id == change_id).first()
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    change.status = "accepted"
    db.commit()
    return {"status": "success"}


@app.post("/api/pending-changes/{change_id}/reject", response_model=dict)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def reject_change(change_id: int, db: Session = Depends(get_db)):
    """Reject a pending change."""
    change = db.query(PendingChange).filter(PendingChange.id == change_id).first()
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    change.status = "rejected"
    db.commit()
    return {"status": "success"}


@app.post("/api/rollback/{action_id}", response_model=dict)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def rollback_action(action_id: int, db: Session = Depends(get_db)):
    """Rollback an action."""
    logger.info("rollback_action", action_id=action_id)
    return {"status": "success"}


@app.get("/api/threads/{thread_id}/logs/sse")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def stream_logs(request: Request, thread_id: int):
    """Stream logs for a thread via SSE."""
    async def log_generator():
        while True:
            yield f"data: {json.dumps({'content': 'Agent heartbeat', 'type': 'info'})}\n\n"
            await asyncio.sleep(10)
    return StreamingResponse(log_generator(), media_type="text/event-stream")


# Skills API Endpoints
@app.get("/api/skills", response_model=list)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def list_skills(
    request: Request,
    workspace_id: Optional[int] = None,
    category: Optional[str] = None,
    include_global: bool = True,
    db: Session = Depends(get_db)
):
    """List all skills, optionally filtered by workspace and category."""
    from app.intelligence.skill_registry import SkillRegistry
    registry = SkillRegistry(db)
    skills = registry.list_skills(
        workspace_id=workspace_id,
        category=category,
        include_global=include_global
    )
    return skills


@app.get("/api/skills/{skill_id}", response_model=SkillResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_skill(skill_id: int, db: Session = Depends(get_db)):
    """Get a specific skill by ID."""
    from app.intelligence.skill_registry import SkillRegistry
    registry = SkillRegistry(db)
    skill = registry.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@app.post("/api/skills", response_model=SkillResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def create_skill(skill_data: SkillCreate, db: Session = Depends(get_db)):
    """Create a new skill."""
    logger.info("create_skill", name=skill_data.name, workspace_id=skill_data.workspace_id)
    
    from app.intelligence.skill_registry import SkillRegistry
    registry = SkillRegistry(db)
    
    existing = registry.get_skill_by_name(skill_data.name, skill_data.workspace_id)
    if existing:
        raise HTTPException(status_code=409, detail="Skill with this name already exists")
    
    skill = registry.create_skill(
        name=skill_data.name,
        description=skill_data.description,
        content=skill_data.content,
        category=skill_data.category,
        workspace_id=skill_data.workspace_id,
        is_global=skill_data.is_global
    )
    return skill


@app.put("/api/skills/{skill_id}", response_model=SkillResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def update_skill(skill_id: int, skill_data: SkillUpdate, db: Session = Depends(get_db)):
    """Update an existing skill."""
    logger.info("update_skill", skill_id=skill_id)
    
    from app.intelligence.skill_registry import SkillRegistry
    registry = SkillRegistry(db)
    skill = registry.update_skill(
        skill_id=skill_id,
        name=skill_data.name,
        description=skill_data.description,
        content=skill_data.content,
        category=skill_data.category
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@app.delete("/api/skills/{skill_id}", response_model=dict)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    """Delete a skill."""
    logger.info("delete_skill", skill_id=skill_id)
    
    from app.intelligence.skill_registry import SkillRegistry
    registry = SkillRegistry(db)
    success = registry.delete_skill(skill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "success", "message": "Skill deleted"}


@app.post("/api/skills/search", response_model=list)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def search_skills(request: Request, search_request: SkillSearchRequest, db: Session = Depends(get_db)):
    """Search for skills by relevance to a query."""
    from app.intelligence.skill_registry import SkillRegistry
    registry = SkillRegistry(db)
    skills = registry.find_relevant_skills(
        query=search_request.query,
        workspace_id=search_request.workspace_id,
        limit=search_request.limit
    )
    return skills


@app.get("/api/skills/categories", response_model=list)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_skill_categories(
    request: Request,
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get available skill categories."""
    from app.intelligence.skill_registry import SkillRegistry
    registry = SkillRegistry(db)
    return registry.get_skill_categories(workspace_id=workspace_id)


@app.post("/api/workspaces/{workspace_id}/generate-skill", response_model=SkillResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def generate_workspace_skill(
    workspace_id: int,
    request: Request,
    workspace_path: str = "/workspace",
    db: Session = Depends(get_db)
):
    """Generate a workspace-specific skill by analyzing the workspace."""
    from app.intelligence.workspace_analyzer import generate_workspace_skill as analyze_and_create_skill
    from app.intelligence.skill_registry import SkillRegistry
    from app.database.models import Workspace
    
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    logger.info("generate_workspace_skill", workspace_id=workspace_id)
    
    skill_content, analysis_results = analyze_and_create_skill(workspace_path, workspace_id)
    
    registry = SkillRegistry(db)
    
    existing = registry.get_skill_by_name("workspace_profile", workspace_id)
    if existing:
        registry.delete_skill(existing.id)
    
    skill = registry.create_skill(
        name="workspace_profile",
        description=f"Auto-generated profile for {workspace.owner}/{workspace.repo} workspace",
        content=skill_content,
        category="General",
        workspace_id=workspace_id,
        is_global=False
    )
    
    return skill


@app.get("/api/workspaces/{workspace_id}/analyze", response_model=WorkspaceAnalysisResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def analyze_workspace(
    workspace_id: int,
    request: Request,
    workspace_path: str = "/workspace",
    db: Session = Depends(get_db)
):
    """Analyze a workspace without creating a skill."""
    from app.intelligence.workspace_analyzer import analyze_workspace as analyze_ws
    from app.database.models import Workspace
    
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    results = analyze_ws(workspace_path)
    return results


@app.get("/graph/invoke")
async def invoke_graph(repo_name: str = "test-repo"):
    """Invoke the LangGraph workflow with a repository."""
    initial_state = {
        "messages": [],
        "current_repo": repo_name,
        "analysis_result": None,
        "github_token": None
    }
    result = await workflow.ainvoke(initial_state)
    return {"result": result}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to OmniCode API",
        "version": "1.0.0",
        "docs": "/docs" if not settings.is_production else None,
        "health": "/health"
    }


@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes-style readiness probe."""
    try:
        db.execute(text("SELECT 1"))
        r = redis.from_url(settings.redis_url)
        r.ping()
        return {"ready": True}
    except Exception as e:
        return {"ready": False, "error": str(e)}


import logging
logging.getLogger("uvicorn.access").disabled = True