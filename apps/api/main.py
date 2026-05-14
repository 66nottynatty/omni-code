"""
OmniCode FastAPI main application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import redis.asyncio as redis
import structlog
import asyncio
import os

from app.core.config import get_settings
from app.core.exceptions import (
    omni_exception_handler,
    generic_exception_handler,
    OmniCodeException,
)
from app.database.session import AsyncSessionLocal
from app.routers import (
    tasks, skills, threads, changes, workspaces, rollback,
    repos, auth, orchestrator, graphs, stream, system, terminal, preview
)

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
    from app.core.scheduler import get_scheduler_manager
    
    # Initialize Redis connection
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        app.state.redis = None
    
    # Start the scheduler
    scheduler_manager = get_scheduler_manager()
    scheduler_manager.start()
    app.state.scheduler = scheduler_manager
    
    # Recover any interrupted task graphs
    asyncio.create_task(recover_interrupted_tasks(app.state.redis))

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
        logger.info("mcp_servers_ready")
    except Exception as e:
        logger.warning("mcp_startup_failed", error=str(e))
        app.state.mcp = None
    
    yield
    
    # Cleanup
    scheduler_manager.stop()
    if hasattr(app.state, 'mcp') and app.state.mcp:
        await app.state.mcp.close_all()

app = FastAPI(
    title="OmniCode API",
    description="AI-powered code analysis and automation platform",
    version="1.1.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
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
app.include_router(auth.router, prefix="/api")
app.include_router(repos.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(graphs.router, prefix="/api")
app.include_router(orchestrator.router, prefix="/api")
app.include_router(threads.router, prefix="/api")
app.include_router(changes.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(rollback.router, prefix="/api")
app.include_router(stream.router, prefix="/api")
app.include_router(preview.router, prefix="/api")
app.include_router(system.router)
app.include_router(terminal.router)


async def recover_interrupted_tasks(redis_client):
    """Recover and resume any interrupted task graphs."""
    try:
        from app.orchestrator.engine import OrchestratorEngine
        async with AsyncSessionLocal() as db:
            engine_inst = OrchestratorEngine(db_session=db, redis_client=redis_client)
            await engine_inst.recover_running_graphs()
        logger.info("task_recovery_complete")
    except Exception as e:
        logger.error("task_recovery_failed", error=str(e))
