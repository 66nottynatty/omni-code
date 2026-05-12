"""
OmniCode FastAPI main application.
Consolidated and production-hardened.
"""

import os
import json
import uuid
import asyncio
import redis
import structlog
from datetime import datetime
from typing import Optional, AsyncGenerator, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from github import Github

from app.core.config import get_settings
from app.core.security import security_manager
from app.core.exceptions import (
    omni_exception_handler,
    generic_exception_handler,
    OmniCodeException,
)
from app.database.session import engine as db_engine, get_db, AsyncSessionLocal
from app.database.models import User, Workspace, CodeChunk

# Routers
from app.orchestrator.router import router as orchestrator_router
from app.routers.tasks import router as tasks_router
from app.routers.skills import router as skills_router
from app.routers.threads import router as threads_router
from app.routers.changes import router as changes_router
from app.routers.workspaces import router as workspaces_router

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.scheduler import start_scheduler
    
    # Initialize Redis connection
    try:
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        app.state.redis = redis_client
        logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        app.state.redis = None
    
    # Start the scheduler
    start_scheduler()
    
    yield
    
    # Cleanup
    if app.state.redis:
        app.state.redis.close()

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

# Mount specialized routers
app.include_router(orchestrator_router)
app.include_router(tasks_router)
app.include_router(skills_router)
app.include_router(threads_router)
app.include_router(changes_router)
app.include_router(workspaces_router)

# ============================================================================
# Helper Functions
# ============================================================================

def get_user_github_token(user_id: int, db: Session) -> str:
    user = db.query(User).get(user_id)
    if not user or not user.access_token_encrypted:
        return settings.github_token
    return security_manager.decrypt_token(user.access_token_encrypted)

async def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    if not authorization:
        return 1  # Dev fallback
    user_id = security_manager.validate_bearer_token(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return int(user_id)

# ============================================================================
# Health & Info
# ============================================================================

@app.get("/health")
async def health():
    db_ok = False
    redis_ok = False
    
    try:
        with db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass
    
    try:
        if app.state.redis:
            app.state.redis.ping()
            redis_ok = True
    except Exception:
        pass
    
    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected"
    }

# ============================================================================
# Repository Endpoints
# ============================================================================

@app.get("/api/repos/{owner}/{repo}/tree")
async def get_repo_tree(
    owner: str,
    repo: str,
    branch: str = "main",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    token = get_user_github_token(user_id, db)
    try:
        g = Github(token)
        r = g.get_repo(f"{owner}/{repo}")
        tree = r.get_git_tree(branch, recursive=True)
        return {"tree": [{"path": item.path, "type": item.type} for item in tree.tree]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/repos/{owner}/{repo}/file")
async def get_repo_file(
    owner: str,
    repo: str,
    path: str,
    branch: str = "main",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    token = get_user_github_token(user_id, db)
    try:
        g = Github(token)
        r = g.get_repo(f"{owner}/{repo}")
        content = r.get_contents(path, ref=branch)
        return {"content": content.decoded_content.decode()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================================
# WebSocket Terminal
# ============================================================================

@app.websocket("/ws/terminal/{session_id}")
async def terminal_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    process = await asyncio.create_subprocess_shell(
        "/bin/bash",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "TERM": "xterm-256color"}
    )
    
    async def read_output():
        while True:
            data = await process.stdout.read(1024)
            if not data: break
            await websocket.send_text(data.decode(errors='replace'))

    output_task = asyncio.create_task(read_output())
    
    try:
        while True:
            data = await websocket.receive_text()
            if data.startswith("{"):
                continue # Ignore resize etc for now
            process.stdin.write(data.encode())
            await process.stdin.drain()
    except WebSocketDisconnect:
        pass
    finally:
        output_task.cancel()
        process.terminate()
        await process.wait()

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
        },
        {
            "id": "gpt-4-turbo",
            "name": "GPT-4 Turbo",
            "provider": "OpenAI",
            "context_window": "128k",
            "cost_tier": "pro"
        },
        {
            "id": "gpt-3.5-turbo",
            "name": "GPT-3.5 Turbo",
            "provider": "OpenAI",
            "context_window": "16k",
            "cost_tier": "standard"
        },
        {
            "id": "claude-3-5-sonnet",
            "name": "Claude 3.5 Sonnet",
            "provider": "Anthropic",
            "context_window": "200k",
            "cost_tier": "pro"
        }
    ]
