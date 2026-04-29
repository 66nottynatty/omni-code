from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import get_settings
from app.graphs.workflow import workflow
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


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


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "omnicode-backend"}


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
