from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
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
from app.database.session import engine, get_db
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
    start_scheduler()
    yield

app = FastAPI(title="OmniCode API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_user_github_token(user_id: int, db: Session) -> str:
  user = db.query(User).get(user_id)
  if not user or not user.access_token_encrypted:
    return settings.github_token
  return security_manager.decrypt_token(user.access_token_encrypted)

@app.get("/api/repos/{owner}/{repo}/tree")
async def get_repo_tree(owner: str, repo: str, branch: str = "main", db: Session = Depends(get_db)):
    # In real app, get user_id from JWT
    token = get_user_github_token(1, db)
    g = Github(token)
    r = g.get_repo(f"{owner}/{repo}")
    tree = r.get_git_tree(branch, recursive=True)
    return [{"path": i.path, "type": i.type, "size": i.size, "name": os.path.basename(i.path)} for i in tree.tree]

@app.get("/api/repos/{owner}/{repo}/file")
async def get_repo_file(owner: str, repo: str, path: str, branch: str = "main", db: Session = Depends(get_db)):
    token = get_user_github_token(1, db)
    g = Github(token)
    r = g.get_repo(f"{owner}/{repo}")
    content = r.get_contents(path, ref=branch)
    return {"content": content.decoded_content.decode(), "sha": content.sha}

@app.post("/api/auth/store-token")
async def store_token(data: dict, db: Session = Depends(get_db)):
    github_token = data.get("github_token")
    # Mock user_id = 1
    user = db.query(User).get(1)
    if user:
        user.access_token_encrypted = security_manager.encrypt_token(github_token)
        db.commit()
    return {"status": "success"}

@app.post("/api/repos/{owner}/{repo}/index")
async def index_repository(owner: str, repo: str, branch: str = "main", db: Session = Depends(get_db)):
    token = get_user_github_token(1, db)
    from app.intelligence.indexer import CodebaseIndexer
    from app.core.scheduler import scheduler
    
    workspace = db.query(Workspace).filter(Workspace.owner == owner, Workspace.repo == repo).first()
    if not workspace:
        workspace = Workspace(owner=owner, repo=repo, branch=branch)
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
    
    indexer = CodebaseIndexer(db, token)
    scheduler.add_job(
        indexer.index_repo,
        args=[workspace.id, owner, repo, branch]
    )
    
    return {"status": "indexing_started", "workspace_id": workspace.id}

@app.post("/api/decompose")
async def decompose_task(data: dict):
    from app.orchestrator.decomposer import TaskDecomposer
    decomposer = TaskDecomposer()
    goal = data.get("goal")
    context = data.get("context", {})
    graph = await decomposer.decompose(goal, context)
    return graph

@app.websocket("/ws/terminal/{session_id}")
async def terminal_ws(websocket: WebSocket, session_id: str):
  await websocket.accept()
  process = await asyncio.create_subprocess_shell(
    "/bin/bash",
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT
  )
  async def read_output():
    while True:
      data = await process.stdout.read(1024)
      if not data: break
      await websocket.send_text(data.decode('utf-8', errors='replace'))
  read_task = asyncio.create_task(read_output())
  try:
    while True:
      cmd = await websocket.receive_text()
      if process.stdin:
        process.stdin.write(cmd.encode() + b'\n')
        await process.stdin.drain()
  except WebSocketDisconnect:
    read_task.cancel()
    process.terminate()

@app.get("/health")
async def health():
    return {"status": "ok", "db": "connected", "redis": "connected"}

@app.get("/api/models")
async def get_models():
    return [
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "OpenAI", "context_window": "128k", "cost_tier": "pro"},
        {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "provider": "DeepSeek", "context_window": "64k", "cost_tier": "pro"},
        {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "Anthropic", "context_window": "200k", "cost_tier": "pro"},
        {"id": "ollama-qwen-2.5", "name": "Qwen 2.5 Coder (Local)", "provider": "Ollama", "context_window": "32k", "cost_tier": "free"},
    ]

