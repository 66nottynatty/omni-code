import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..database.session import get_async_db
from ..orchestrator.engine import OrchestratorEngine
from ..orchestrator.decomposer import TaskDecomposer
from ..schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
    TaskGraph,
    SubTask,
    TaskStatus
)
import structlog
import json
import asyncio
from fastapi.responses import StreamingResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.post("/run", response_model=OrchestratorResponse)
async def run_orchestrator(
    request_data: OrchestratorRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Start a new orchestration workflow.
    """
    logger.info(
        "orchestrator_run_request",
        workspace_id=request_data.workspace_id,
        prefer_local=request_data.prefer_local
    )
    
    engine = OrchestratorEngine(db_session=db)
    graph = await engine.execute_workflow(
        request_data.prompt,
        request_data.workspace_id,
        request_data.prefer_local
    )
    
    return OrchestratorResponse(
        graph_id=graph.id,
        status=graph.status.value
    )


@router.post("/preview", response_model=TaskGraph)
async def preview_orchestrator(
    request_data: OrchestratorRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Preview the decomposition of a prompt without executing.
    """
    logger.info(
        "orchestrator_preview_request",
        workspace_id=request_data.workspace_id
    )
    
    engine = OrchestratorEngine(db_session=db)
    context = {
        "workspace_id": request_data.workspace_id,
        "prefer_local": request_data.prefer_local
    }
    graph = await engine.decomposer.decompose(request_data.prompt, context, db=db)
    
    # Add timestamps for schema if needed
    if not graph.created_at:
        graph.created_at = datetime.utcnow().isoformat()
    if not graph.updated_at:
        graph.updated_at = datetime.utcnow().isoformat()
        
    return graph


@router.post("/decompose")
async def decompose_task(data: dict, db: AsyncSession = Depends(get_async_db)):
    """
    Decompose a goal into a task graph.
    """
    decomposer = TaskDecomposer()
    goal = data.get("goal")
    context = data.get("context", {})
    
    if not goal:
        raise HTTPException(status_code=400, detail="Goal is required")
    
    graph = await decomposer.decompose(goal, context, db=db)
    return graph


@router.post("/decompose/analyze")
async def analyze_complexity(data: dict):
    """Quick complexity analysis for a goal."""
    goal = data.get("goal", "")
    if not goal:
        raise HTTPException(status_code=400, detail="Goal is required")
    
    # Heuristic-based complexity analysis
    words = goal.lower().split()
    word_count = len(words)
    
    # Keywords that suggest high complexity
    complex_keywords = ["refactor", "migrate", "security", "optimization", "architecture", "integration"]
    complex_count = sum(1 for word in words if word in complex_keywords)
    
    complexity = min(1.0, (word_count / 50.0) + (complex_count * 0.1))
    estimated_tasks = max(1, int(complexity * 10))
    
    return {
        "complexity": round(complexity, 2),
        "estimated_tasks": estimated_tasks,
        "confidence": 0.8
    }


@router.post("/{graph_id}/inject")
async def inject_task_endpoint(
    graph_id: str,
    task_data: Dict[str, Any],
    db: AsyncSession = Depends(get_async_db)
):
    """
    Dynamically inject a new task into a running graph.
    """
    logger.info("injecting_task", graph_id=graph_id, task_id=task_data.get("id"))
    
    engine = OrchestratorEngine(db_session=db)
    
    new_task = SubTask(
        id=task_data.get("id", f"task-{uuid.uuid4().hex[:8]}"),
        title=task_data.get("title", "Injected task"),
        description=task_data.get("description", ""),
        agent_type=task_data.get("agent_type", "backend"),
        dependencies=task_data.get("dependencies", []),
        status=TaskStatus.PENDING,
        input_data=task_data.get("input_data", {}),
        max_retries=task_data.get("max_retries", 3)
    )
    
    success = await engine.inject_task(graph_id, new_task)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Graph not found or not in active state"
        )
    
    return {"status": "success", "task_id": new_task.id}


@router.post("/{graph_id}/cancel")
async def cancel_graph(
    graph_id: str,
    request: Request
):
    """
    Cancel a running graph.
    """
    logger.info("cancelling_graph", graph_id=graph_id)
    
    redis_client = request.app.state.redis
    if redis_client:
        redis_client.set(f"graph_signal_{graph_id}", "cancel")
    
    return {"status": "cancelled"}
