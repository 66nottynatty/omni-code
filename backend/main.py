from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import get_settings
from app.graphs.workflow import workflow
from app.database.session import engine, get_db
from app.database.models import ActionHistory, PendingChange, AgentLog, BackgroundTask, TaskLog, BlockerNotification
from app.tasks import run_agent_task
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
import logging
import json
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
redis_client = redis.from_url(settings.redis_url)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("OmniCode backend starting up...")
    yield
    logger.info("OmniCode backend shutting down...")

app = FastAPI(
    title="OmniCode API",
    description="FastAPI backend with LangGraph for agentic workflows",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/tasks")
async def create_task(workspace_id: int, task_type: str, payload: dict, db: Session = Depends(get_db)):
    task = BackgroundTask(
        workspace_id=workspace_id,
        task_type=task_type,
        payload=payload,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    run_agent_task.delay(task.id)
    return {"task_id": task.id}

@app.get("/api/tasks")
async def list_tasks(workspace_id: int | None = None, status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(BackgroundTask)
    if workspace_id:
        query = query.filter(BackgroundTask.workspace_id == workspace_id)
    if status:
        query = query.filter(BackgroundTask.status == status)
    return query.order_by(BackgroundTask.created_at.desc()).all()

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(BackgroundTask).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/api/tasks/{task_id}/logs/sse")
async def stream_task_logs(task_id: int):
    async def log_generator():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"task_logs_{task_id}")
        
        try:
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    yield f"data: {message['data'].decode('utf-8')}\n\n"
                await asyncio.sleep(0.1)
        finally:
            pubsub.unsubscribe(f"task_logs_{task_id}")

    return StreamingResponse(log_generator(), media_type="text/event-stream")

@app.post("/api/tasks/{task_id}/resolve")
async def resolve_blocker(task_id: int, resolution: str, db: Session = Depends(get_db)):
    task = db.query(BackgroundTask).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    blocker = db.query(BlockerNotification).filter(
        BlockerNotification.task_id == task_id,
        BlockerNotification.resolved == False
    ).first()
    
    if not blocker:
        raise HTTPException(status_code=400, detail="No active blocker found for this task")
    
    blocker.resolved = True
    blocker.resolution = resolution
    
    # Update task status and resume
    task.status = "pending" # So it can be picked up or resumed
    db.commit()
    
    # Resume task (for now we just trigger it again, but in a real scenario 
    # we might want to resume from the exact state)
    # Since we use LangGraph, if we pass the previous messages back in payload, it might "resume"
    
    payload = task.payload or {}
    # Append resolution to messages
    messages = payload.get("messages", [])
    messages.append({"role": "user", "content": f"Human resolution for blocker: {resolution}"})
    payload["messages"] = messages
    task.payload = payload
    db.commit()
    
    run_agent_task.delay(task.id)
    
    return {"status": "success"}

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    health = {"status": "ok", "db": "disconnected", "redis": "disconnected"}
    
    try:
        db.execute(text("SELECT 1"))
        health["db"] = "connected"
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        
    try:
        r = redis.from_url(settings.redis_url)
        if r.ping():
            health["redis"] = "connected"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        
    return health

@app.get("/api/models")
async def get_models():
    return [
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "OpenAI", "context_window": "128k", "cost_tier": "pro"},
        {"id": "deepseek-coder", "name": "DeepSeek Coder", "provider": "DeepSeek", "context_window": "32k", "cost_tier": "free"},
        {"id": "moonshot-v1", "name": "Moonshot V1", "provider": "Moonshot", "context_window": "128k", "cost_tier": "pro"},
    ]

@app.get("/api/threads/{thread_id}/history")
async def get_thread_history(thread_id: int, db: Session = Depends(get_db)):
    history = db.query(ActionHistory).filter(ActionHistory.thread_id == thread_id).order_by(ActionHistory.created_at.desc()).all()
    return history

@app.post("/api/pending-changes/{change_id}/accept")
async def accept_change(change_id: int, db: Session = Depends(get_db)):
    change = db.query(PendingChange).get(change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    change.status = "accepted"
    db.commit()
    return {"status": "success"}

@app.post("/api/pending-changes/{change_id}/reject")
async def reject_change(change_id: int, db: Session = Depends(get_db)):
    change = db.query(PendingChange).get(change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    change.status = "rejected"
    db.commit()
    return {"status": "success"}

@app.post("/api/rollback/{action_id}")
async def rollback_action(action_id: int, db: Session = Depends(get_db)):
    # Mock rollback logic
    return {"status": "success"}

@app.get("/api/threads/{thread_id}/logs/sse")
async def stream_logs(thread_id: int):
    async def log_generator():
        while True:
            # Mock log streaming
            yield f"data: {json.dumps({'content': 'Agent heartbeat', 'type': 'info'})}\n\n"
            await asyncio.sleep(10)
    return StreamingResponse(log_generator(), media_type="text/event-stream")

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
    return {
        "message": "Welcome to OmniCode API",
        "docs": "/docs",
        "health": "/health"
    }
