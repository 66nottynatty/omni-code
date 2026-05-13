"""
OmniCode FastAPI main application with production-ready endpoints.
Includes WebSocket terminal, SSE activity stream, and REST API.
"""

from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, Header
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
import os
import uuid
from datetime import datetime
from typing import Optional, AsyncGenerator
from github import Github

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
from app.database.session import engine, get_db, AsyncSessionLocal
from app.database.models import (
    User,
    Workspace,
    CodeChunk,
    ActionHistory,
    PendingChange,
    AgentLog,
    BackgroundTask,
    TaskLog,
    BlockerNotification,
    AgentSessionModel,
    TaskCheckpointModel,
    SubTaskModel
)
from app.tasks import run_agent_task
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.routers import tasks, skills, threads, changes, workspaces, rollback

# Initialize structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging_level="INFO"),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.scheduler import start_scheduler, get_scheduler_manager
    
    # Initialize Redis connection
    try:
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        app.state.redis = redis_client
        logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        app.state.redis = None
    
    # Start the scheduler with state recovery
    scheduler_manager = get_scheduler_manager()
    scheduler_manager.start()
    app.state.scheduler = scheduler_manager
    
    # Recover any interrupted task graphs
    asyncio.create_task(recover_interrupted_tasks())

    # Register MCP servers
    from app.orchestrator.mcp_manager import MCPManager
    mcp = MCPManager()
    try:
        await mcp.register_server("filesystem", {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
        })
        await mcp.register_server("shell", {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-shell"]
        })
        app.state.mcp = mcp
        logger.info("mcp_servers_ready", tools=mcp.list_tools())
    except Exception as e:
        logger.warning("mcp_startup_failed", error=str(e))
        app.state.mcp = None
    
    yield
    
    # Cleanup
    scheduler_manager.stop()
    if app.state.mcp:
        await app.state.mcp.close_all()

app = FastAPI(
    title="OmniCode API",
    description="AI-powered code analysis and automation platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_exception_handler(OmniCodeException, omni_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include specialized routers
app.include_router(tasks.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(threads.router, prefix="/api")
app.include_router(changes.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api")
app.include_router(rollback.router, prefix="/api")

# ============================================================================
# Helper Functions
# ============================================================================

def get_user_github_token(user_id: int, db: Session) -> str:
    """Retrieve and decrypt user's GitHub token."""
    user = db.query(User).get(user_id)
    if not user or not user.access_token_encrypted:
        return settings.github_token
    return security_manager.decrypt_token(user.access_token_encrypted)


async def get_current_user_id(
    authorization: Optional[str] = Header(None)
) -> int:
    """Extract user ID from Authorization header."""
    if not authorization:
        # Default to first user for development
        return 1
    
    user_id = security_manager.validate_bearer_token(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return int(user_id)


async def recover_interrupted_tasks():
    """Recover and resume any interrupted task graphs."""
    try:
        from app.orchestrator.engine import OrchestratorEngine
        
        async with AsyncSessionLocal() as db:
            engine_inst = OrchestratorEngine(db_session=db, redis_client=app.state.redis)
            await engine_inst.recover_running_graphs()
        
        logger.info("task_recovery_complete")
    except Exception as e:
        logger.error("task_recovery_failed", error=str(e))


# ============================================================================
# Repository Endpoints
# ============================================================================

@app.get("/api/repos/{owner}/{repo}/tree")
@limiter.limit("60/minute")
async def get_repo_tree(
    owner: str,
    repo: str,
    branch: str = "main",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Get repository file tree structure.
    
    Returns a flattened list of all files with metadata.
    """
    token = get_user_github_token(user_id, db)
    
    try:
        g = Github(token)
        r = g.get_repo(f"{owner}/{repo}")
        tree = r.get_git_tree(branch, recursive=True)
        
        files = [
            {
                "path": item.path,
                "type": item.type,
                "size": item.size,
                "name": os.path.basename(item.path),
                "extension": os.path.splitext(item.path)[1]
            }
            for item in tree.tree
        ]
        
        return {
            "owner": owner,
            "repo": repo,
            "branch": branch,
            "files": files,
            "total": len(files)
        }
    except Exception as e:
        logger.error("repo_tree_failed", owner=owner, repo=repo, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/repos/{owner}/{repo}/file")
@limiter.limit("60/minute")
async def get_repo_file(
    owner: str,
    repo: str,
    path: str,
    branch: str = "main",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get file content from repository."""
    token = get_user_github_token(user_id, db)
    
    try:
        g = Github(token)
        r = g.get_repo(f"{owner}/{repo}")
        content = r.get_contents(path, ref=branch)
        
        return {
            "path": path,
            "content": content.decoded_content.decode(),
            "sha": content.sha,
            "encoding": "utf-8"
        }
    except Exception as e:
        logger.error("repo_file_failed", path=path, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/repos/{owner}/{repo}/readme")
@limiter.limit("30/minute")
async def get_repo_readme(
    owner: str,
    repo: str,
    branch: str = "main",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get repository README content."""
    token = get_user_github_token(user_id, db)
    
    try:
        g = Github(token)
        r = g.get_repo(f"{owner}/{repo}")
        readme = r.get_readme()
        
        return {
            "content": readme.decoded_content.decode(),
            "name": readme.name
        }
    except Exception as e:
        return {"content": "", "name": "README.md"}


# ============================================================================
# GitHub Token Management
# ============================================================================

@app.post("/api/auth/store-token")
async def store_token(
    data: dict,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Store user's GitHub token with Fernet encryption.
    
    The token is encrypted before storage and can only
    be decrypted by the server using the encryption key.
    """
    github_token = data.get("github_token")
    if not github_token:
        raise HTTPException(status_code=400, detail="GitHub token required")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Create user if not exists
        user = User(id=user_id, username=f"user_{user_id}")
        db.add(user)
    
    # Encrypt and store
    encrypted = security_manager.encrypt_token(github_token)
    user.access_token_encrypted = encrypted
    db.commit()
    
    logger.info("token_stored", user_id=user_id)
    
    return {"status": "success", "message": "Token stored securely"}


@app.delete("/api/auth/token")
async def delete_token(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Delete user's stored GitHub token."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.access_token_encrypted = None
        db.commit()
    
    return {"status": "success"}


@app.get("/api/auth/token-status")
async def get_token_status(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Check if user has a stored GitHub token."""
    user = db.query(User).filter(User.id == user_id).first()
    
    return {
        "has_token": bool(user and user.access_token_encrypted),
        "token_type": "encrypted"
    }


# ============================================================================
# Codebase Indexing
# ============================================================================

@app.post("/api/repos/{owner}/{repo}/index")
async def index_repository(
    owner: str,
    repo: str,
    branch: str = "main",
    incremental: bool = True,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Start repository indexing job.
    """
    token = get_user_github_token(user_id, db)
    
    # Get or create workspace
    workspace = db.query(Workspace).filter(
        Workspace.owner == owner,
        Workspace.repo == repo,
        Workspace.branch == branch
    ).first()
    
    if not workspace:
        workspace = Workspace(
            owner=owner,
            repo=repo,
            branch=branch
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
    
    # Start indexing job
    from app.intelligence.indexer import CodebaseIndexer
    from app.core.scheduler import scheduler
    
    # Add background job
    job_id = f"index_{workspace.id}_{datetime.utcnow().timestamp()}"
    scheduler.add_job(
        _run_indexing,
        'date',
        run_date=datetime.utcnow(),
        args=[workspace.id, owner, repo, branch, incremental, token],
        id=job_id,
        replace_existing=True
    )
    
    logger.info("indexing_started", workspace_id=workspace.id, job_id=job_id)
    
    return {
        "status": "indexing_started",
        "workspace_id": workspace.id,
        "job_id": job_id
    }


async def _run_indexing(workspace_id: int, owner: str, repo: str, branch: str, incremental: bool, token: str):
    """Background indexing task."""
    from app.intelligence.indexer import CodebaseIndexer
    from app.database.session import SessionLocal
    
    db = SessionLocal()
    try:
        indexer = CodebaseIndexer(db, token)
        stats = await indexer.index_repo(workspace_id, owner, repo, branch, incremental)
        logger.info("indexing_complete", workspace_id=workspace_id, stats=stats)
    except Exception as e:
        logger.error("indexing_failed", workspace_id=workspace_id, error=str(e))
    finally:
        db.close()


@app.get("/api/repos/{owner}/{repo}/index/status")
async def get_index_status(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get indexing status and statistics for a repository."""
    workspace = db.query(Workspace).filter(
        Workspace.owner == owner,
        Workspace.repo == repo
    ).first()
    
    if not workspace:
        return {"status": "not_indexed"}
    
    chunk_count = db.query(CodeChunk).filter(
        CodeChunk.workspace_id == workspace.id
    ).count()
    
    return {
        "workspace_id": workspace.id,
        "status": "indexed",
        "chunk_count": chunk_count,
        "last_updated": workspace.created_at.isoformat()
    }


@app.post("/api/repos/{owner}/{repo}/search")
async def search_code(
    owner: str,
    repo: str,
    query: str,
    limit: int = 5,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Search indexed code using vector similarity."""
    workspace = db.query(Workspace).filter(
        Workspace.owner == owner,
        Workspace.repo == repo
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Repository not indexed")
    
    from app.intelligence.indexer import CodebaseIndexer
    indexer = CodebaseIndexer(db)
    results = await indexer.search_similar(workspace.id, query, limit)
    
    return {"results": results}


# ============================================================================
# Task Decomposition
# ============================================================================

@app.post("/api/decompose")
async def decompose_task(data: dict):
    """
    Decompose a goal into a task graph using DeepSeek-Reasoner.
    """
    from app.orchestrator.decomposer import TaskDecomposer
    
    decomposer = TaskDecomposer()
    goal = data.get("goal")
    context = data.get("context", {})
    
    if not goal:
        raise HTTPException(status_code=400, detail="Goal is required")
    
    # Choose decomposition method based on complexity
    fast_mode = data.get("fast", False)
    
    if fast_mode:
        graph = await decomposer.decompose_fast(goal, context)
    else:
        graph = await decomposer.decompose(goal, context)
    
    return graph


@app.post("/api/decompose/analyze")
async def analyze_complexity(data: dict):
    """Quick complexity analysis for a goal."""
    from app.orchestrator.decomposer import TaskDecomposer
    
    decomposer = TaskDecomposer()
    goal = data.get("goal")
    
    if not goal:
        raise HTTPException(status_code=400, detail="Goal is required")
    
    analysis = await decomposer.analyze_complexity(goal)
    return analysis


# ============================================================================
# WebSocket Terminal
# ============================================================================

class TerminalSession:
    """Manages a terminal session with bi-directional communication."""
    
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.process: Optional[asyncio.subprocess.Process] = None
        self._output_task: Optional[asyncio.Task] = None
        self._input_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the terminal process."""
        self.process = await asyncio.create_subprocess_shell(
            "/bin/bash",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "TERM": "xterm-256color"}
        )
        
        # Start reading output
        self._output_task = asyncio.create_task(self._read_output())
        
        # Handle resize
        asyncio.create_task(self._handle_resize())
        
        logger.info("terminal_started", session_id=self.session_id)

    async def _read_output(self):
        """Read process output and send to WebSocket."""
        while self.process and self.process.stdout:
            try:
                data = await self.process.stdout.read(1024)
                if not data:
                    break
                
                await self.websocket.send_text(data.decode('utf-8', errors='replace'))
            except Exception as e:
                logger.error("terminal_read_error", error=str(e))
                break

    async def _handle_resize(self):
        """Handle terminal resize messages."""
        while True:
            try:
                msg = await self.websocket.receive_text()
                data = json.loads(msg)
                
                if data.get("type") == "resize":
                    cols = data.get("cols", 80)
                    rows = data.get("rows", 24)
                    logger.debug("terminal_resize", cols=cols, rows=rows)
                    
            except json.JSONDecodeError:
                # Treat as command input
                if self.process and self.process.stdin:
                    cmd = msg.encode() + b'\n'
                    self.process.stdin.write(cmd)
                    await self.process.stdin.drain()
            except Exception:
                break

    async def send_input(self, data: str):
        """Send input to the terminal process."""
        if self.process and self.process.stdin:
            self.process.stdin.write(data.encode())
            await self.process.stdin.drain()

    async def close(self):
        """Clean up the terminal session."""
        if self._output_task:
            self._output_task.cancel()
        if self._input_task:
            self._input_task.cancel()
        if self.process:
            self.process.terminate()
            try:
                await self.process.wait()
            except Exception:
                pass
        
        logger.info("terminal_closed", session_id=self.session_id)


# Active terminal sessions
terminal_sessions: dict[str, TerminalSession] = {}


@app.websocket("/ws/terminal/{session_id}")
async def terminal_ws(websocket: WebSocket, session_id: str):
    """
    Bi-directional WebSocket terminal handler.
    """
    await websocket.accept()
    
    session = TerminalSession(websocket, session_id)
    terminal_sessions[session_id] = session
    
    try:
        await session.start()
        
        # Keep connection alive and handle bidirectional messages
        while True:
            try:
                data = await websocket.receive_text()
                
                # Check for control messages
                if data.startswith("{"):
                    try:
                        msg = json.loads(data)
                        if msg.get("type") == "resize":
                            cols = msg.get("cols", 80)
                            rows = msg.get("rows", 24)
                            logger.debug("terminal_resize_received", cols=cols, rows=rows)
                    except json.JSONDecodeError:
                        pass
                else:
                    # Regular input - send to terminal
                    await session.send_input(data)
                    
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error("terminal_error", session_id=session_id, error=str(e))
    finally:
        await session.close()
        if session_id in terminal_sessions:
            del terminal_sessions[session_id]


@app.get("/ws/terminal/{session_id}/status")
async def get_terminal_status(session_id: str):
    """Get terminal session status."""
    if session_id in terminal_sessions:
        return {
            "session_id": session_id,
            "active": True
        }
    return {
        "session_id": session_id,
        "active": False
    }


# ============================================================================
# SSE Activity Stream
# ============================================================================

@app.get("/api/stream/{graph_id}")
async def stream_activity(
    graph_id: str,
    authorization: Optional[str] = Header(None)
) -> StreamingResponse:
    """
    Server-Sent Events stream for real-time activity updates.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        redis_client = app.state.redis
        
        # If no Redis, use polling fallback
        if not redis_client:
            yield "data: {\"type\": \"connected\", \"graph_id\": \"" + graph_id + "\"}\n\n"
            import time
            for _ in range(100):  # Max 100 messages
                yield "data: {\"type\": \"heartbeat\"}\n\n"
                time.sleep(5)
            return
        
        # Subscribe to Redis channels
        try:
            pubsub = redis_client.pubsub()
            pubsub.subscribe(f"graph_updates_{graph_id}", f"agent_logs_{graph_id}")
            
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    data = message.get("data", b"").decode()
                    yield f"data: {data}\n\n"
                else:
                    # Send keepalive
                    yield ": keepalive\n\n"
                    
        except Exception as e:
            logger.error("sse_stream_error", error=str(e))
            yield f"data: {{\"type\": \"error\", \"message\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/stream/agent/{task_id}")
async def stream_agent_logs(
    task_id: str,
    authorization: Optional[str] = Header(None)
) -> StreamingResponse:
    """Stream logs for a specific agent/task."""
    async def event_generator() -> AsyncGenerator[str, None]:
        redis_client = app.state.redis
        
        if not redis_client:
            yield "data: {\"type\": \"connected\", \"task_id\": \"" + task_id + "\"}\n\n"
            import time
            for _ in range(50):
                yield "data: {\"type\": \"heartbeat\"}\n\n"
                time.sleep(5)
            return
        
        try:
            pubsub = redis_client.pubsub()
            pubsub.subscribe(f"agent_logs_{task_id}")
            
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    data = message.get("data", b"").decode()
                    yield f"data: {data}\n\n"
                else:
                    yield ": keepalive\n\n"
                    
        except Exception as e:
            logger.error("agent_log_stream_error", error=str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================================================
# Task Graph Management
# ============================================================================

@app.get("/api/graphs/{graph_id}")
async def get_graph(graph_id: str):
    """Get task graph details."""
    from app.database.session import SessionLocal
    from app.database.models import TaskGraphModel, SubTaskModel
    from app.schemas.orchestrator import TaskStatus
    
    db = SessionLocal()
    try:
        graph = db.query(TaskGraphModel).filter(
            TaskGraphModel.id == graph_id
        ).first()
        
        if not graph:
            raise HTTPException(status_code=404, detail="Graph not found")
        
        subtasks = db.query(SubTaskModel).filter(
            SubTaskModel.graph_id == graph_id
        ).all()
        
        return {
            "id": graph.id,
            "goal": graph.goal,
            "status": graph.status,
            "subtasks": [
                {
                    "id": st.id,
                    "title": st.title,
                    "description": st.description,
                    "agent_type": st.agent_type,
                    "status": st.status,
                    "dependencies": st.dependencies or [],
                    "output_data": st.output_data,
                    "retry_count": st.retry_count,
                    "completed_at": st.completed_at.isoformat() if st.completed_at else None
                }
                for st in subtasks
            ],
            "created_at": graph.created_at.isoformat(),
            "updated_at": graph.updated_at.isoformat()
        }
    finally:
        db.close()


@app.get("/api/graphs")
async def list_graphs(
    workspace_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 20
):
    """List task graphs with optional filtering."""
    from app.database.session import SessionLocal
    from app.database.models import TaskGraphModel
    
    db = SessionLocal()
    try:
        query = db.query(TaskGraphModel)
        
        if workspace_id:
            query = query.filter(TaskGraphModel.workspace_id == workspace_id)
        if status:
            query = query.filter(TaskGraphModel.status == status)
        
        graphs = query.order_by(
            TaskGraphModel.created_at.desc()
        ).limit(limit).all()
        
        return {
            "graphs": [
                {
                    "id": g.id,
                    "goal": g.goal,
                    "status": g.status,
                    "workspace_id": g.workspace_id,
                    "created_at": g.created_at.isoformat()
                }
                for g in graphs
            ],
            "total": len(graphs)
        }
    finally:
        db.close()


# ============================================================================
# Orchestrator Endpoints
# ============================================================================

@app.post("/api/orchestrator/run")
async def run_orchestrator(data: dict):
    """
    Run the orchestrator with a user prompt.
    """
    from app.orchestrator.engine import OrchestratorEngine
    
    prompt = data.get("prompt")
    workspace_id = data.get("workspace_id", 1)
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    
    async with AsyncSessionLocal() as db:
        try:
            engine_inst = OrchestratorEngine(
                db_session=db,
                redis_client=app.state.redis
            )
            
            graph = await engine_inst.execute_workflow(
                prompt=prompt,
                workspace_id=workspace_id,
                prefer_local=data.get("prefer_local", False)
            )
            
            return {
                "graph_id": graph.id,
                "status": graph.status.value,
                "subtasks_count": len(graph.subtasks)
            }
        except Exception as e:
            logger.error("orchestrator_run_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/orchestrator/preview")
async def preview_orchestrator(data: dict):
    """
    Preview what the orchestrator would do without executing.
    """
    from app.orchestrator.decomposer import TaskDecomposer
    
    prompt = data.get("prompt")
    context = data.get("context", {})
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    
    decomposer = TaskDecomposer()
    graph = await decomposer.decompose(prompt, context)
    
    return {
        "subtasks": [
            {
                "title": st.title,
                "agent_type": st.agent_type,
                "dependencies": st.dependencies
            }
            for st in graph.subtasks
        ]
    }


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    db_ok = False
    redis_ok = False
    
    # Check database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass
    
    # Check Redis
    try:
        if app.state.redis:
            app.state.redis.ping()
            redis_ok = True
    except Exception:
        pass
    
    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
        "version": "1.0.0"
    }


@app.get("/api/models")
async def get_models():
    """Get available AI models."""
    return [
        {
            "id": "deepseek-reasoner",
            "name": "DeepSeek Reasoner",
            "provider": "DeepSeek",
            "context_window": "64k",
            "cost_tier": "pro",
            "reasoning": True
        },
        {
            "id": "deepseek-chat",
            "name": "DeepSeek Chat",
            "provider": "DeepSeek",
            "context_window": "128k",
            "cost_tier": "standard"
        }
    ]


@app.get("/api/info")
async def get_info():
    """Get API information."""
    return {
        "name": "OmniCode API",
        "version": "1.0.0",
        "description": "AI-powered code analysis and automation platform",
        "endpoints": {
            "repos": "/api/repos/{owner}/{repo}",
            "decompose": "/api/decompose",
            "orchestrator": "/api/orchestrator",
            "terminal": "/ws/terminal/{session_id}",
            "stream": "/api/stream/{graph_id}"
        }
    }
