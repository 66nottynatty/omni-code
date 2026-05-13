from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
import time
from app.database.session import engine
from app.schemas import HealthResponse

router = APIRouter(tags=["system"])

@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    """Health check endpoint."""
    db_ok = False
    redis_ok = False
    db_latency = None
    redis_latency = None
    
    # Check database
    start_time = time.time()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
            db_latency = (time.time() - start_time) * 1000
    except Exception:
        pass
    
    # Check Redis
    start_time = time.time()
    try:
        redis_client = request.app.state.redis
        if redis_client:
            redis_client.ping()
            redis_ok = True
            redis_latency = (time.time() - start_time) * 1000
    except Exception:
        pass
    
    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "db": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
        "db_latency_ms": db_latency,
        "redis_latency_ms": redis_latency
    }

@router.get("/api/models")
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
            "id": "gpt-4o",
            "name": "GPT-4o",
            "provider": "OpenAI",
            "context_window": "128k",
            "cost_tier": "pro"
        },
        {
            "id": "claude-3-5-sonnet-20240620",
            "name": "Claude 3.5 Sonnet",
            "provider": "Anthropic",
            "context_window": "200k",
            "cost_tier": "pro"
        }
    ]

@router.get("/api/info")
async def get_info():
    """Get API information."""
    return {
        "name": "OmniCode API",
        "version": "1.0.0",
        "description": "AI-powered code analysis and automation platform",
        "endpoints": {
            "repos": "/api/repos/{owner}/{repo}",
            "decompose": "/api/orchestrator/decompose",
            "orchestrator": "/api/orchestrator",
            "terminal": "/ws/terminal/{session_id}",
            "stream": "/api/stream/{graph_id}"
        }
    }
