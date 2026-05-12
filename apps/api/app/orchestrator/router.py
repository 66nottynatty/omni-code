import uuid
import structlog
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..database.session import get_async_db
from .engine import OrchestratorEngine
from ..schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
    TaskGraph,
    SubTask,
    TaskStatus
)
from ..database.models import TaskGraphModel, SubTaskModel, TaskCheckpointModel

logger = structlog.get_logger()
router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])


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
    graph = await engine.decomposer.decompose(request_data.prompt, context)
    
    # Add timestamps for schema
    graph_dict = graph.model_dump() if hasattr(graph, 'model_dump') else graph.dict()
    graph_dict["created_at"] = datetime.utcnow().isoformat()
    graph_dict["updated_at"] = datetime.utcnow().isoformat()
    
    return graph_dict


@router.get("/{graph_id}", response_model=TaskGraph)
async def get_graph_status(
    graph_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get the current status of a task graph.
    """
    result = await db.execute(select(TaskGraphModel).where(TaskGraphModel.id == graph_id))
    db_graph = result.scalar_one_or_none()
    
    if not db_graph:
        raise HTTPException(status_code=404, detail="Graph not found")
        
    result = await db.execute(select(SubTaskModel).where(SubTaskModel.graph_id == graph_id))
    db_subtasks = result.scalars().all()
    
    subtasks = [
        SubTask(
            id=st.id,
            title=st.title,
            description=st.description,
            agent_type=st.agent_type,
            model_id=st.model_id,
            status=TaskStatus(st.status),
            dependencies=st.dependencies or [],
            input_data=st.input_data or {},
            output_data=st.output_data,
            cost={"amount": st.cost.get("amount", 0) if st.cost else 0, "currency": "USD"} if st.cost else None,
            tokens_used=st.tokens_used or 0,
            retry_count=st.retry_count or 0,
            max_retries=st.max_retries or 3,
            completed_at=st.completed_at.isoformat() if st.completed_at else None
        )
        for st in db_subtasks
    ]
    
    return TaskGraph(
        id=db_graph.id,
        goal=db_graph.goal,
        subtasks=subtasks,
        status=TaskStatus(db_graph.status),
        created_at=db_graph.created_at.isoformat(),
        updated_at=db_graph.updated_at.isoformat()
    )


@router.get("/{graph_id}/stream")
async def stream_graph_logs(graph_id: str, request: Request):
    """
    Stream orchestration logs and updates via SSE.
    """
    async def event_generator():
        from app.core.cache import get_cache
        cache = get_cache()
        redis_client = cache.client
        
        if not redis_client:
            yield f"data: {json.dumps({'type': 'connected', 'graph_id': graph_id})}\n\n"
            counter = 0
            while True:
                if await request.is_disconnected():
                    break
                await asyncio.sleep(5)
                counter += 1
                yield f"data: {json.dumps({'type': 'heartbeat', 'counter': counter})}\n\n"
            return
        
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"graph_updates_{graph_id}", f"agent_logs_{graph_id}")
        
        try:
            yield f"data: {json.dumps({'type': 'connected', 'graph_id': graph_id})}\n\n"
            
            while True:
                if await request.is_disconnected():
                    break
                    
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get('data'):
                    if isinstance(message['data'], bytes):
                        yield f"data: {message['data'].decode('utf-8')}\n\n"
                    else:
                        yield f"data: {json.dumps(message['data'])}\n\n"
                        
                await asyncio.sleep(0.1)
                
        finally:
            pubsub.unsubscribe()
            pubsub.close()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/{graph_id}/inject")
async def inject_task(
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


@router.post("/{graph_id}/modify")
async def modify_graph(
    graph_id: str,
    modifications: Dict[str, Any],
    db: AsyncSession = Depends(get_async_db)
):
    """
    Modify an existing graph.
    """
    logger.info("modifying_graph", graph_id=graph_id)
    
    engine = OrchestratorEngine(db_session=db)
    success = await engine.modify_graph(graph_id, modifications)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Graph not found"
        )
    
    return {"status": "success"}


@router.post("/{graph_id}/cancel")
async def cancel_graph(
    graph_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Cancel a running graph.
    """
    logger.info("cancelling_graph", graph_id=graph_id)
    
    await db.execute(
        update(TaskGraphModel)
        .where(TaskGraphModel.id == graph_id)
        .values(status=TaskStatus.CANCELLED.value)
    )
    await db.commit()
    
    return {"status": "cancelled"}


@router.get("/{graph_id}/checkpoints")
async def get_graph_checkpoints(
    graph_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get all checkpoints for a graph.
    """
    result = await db.execute(
        select(TaskCheckpointModel)
        .where(TaskCheckpointModel.graph_id == graph_id)
        .order_by(TaskCheckpointModel.checkpoint_number)
    )
    checkpoints = result.scalars().all()
    
    return [
        {
            "id": cp.id,
            "checkpoint_number": cp.checkpoint_number,
            "state_snapshot": cp.state_snapshot,
            "created_at": cp.created_at.isoformat()
        }
        for cp in checkpoints
    ]


@router.post("/{graph_id}/recover")
async def recover_graph(
    graph_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Attempt to recover a failed graph by replanning.
    """
    logger.info("recovering_graph", graph_id=graph_id)
    
    result = await db.execute(select(TaskGraphModel).where(TaskGraphModel.id == graph_id))
    db_graph = result.scalar_one_or_none()
    
    if not db_graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    result = await db.execute(select(SubTaskModel).where(SubTaskModel.graph_id == graph_id))
    db_subtasks = result.scalars().all()
    
    subtasks = [
        SubTask(
            id=st.id,
            title=st.title,
            description=st.description,
            agent_type=st.agent_type,
            status=TaskStatus(st.status),
            dependencies=st.dependencies or [],
            input_data=st.input_data or {},
            output_data=st.output_data,
            retry_count=st.retry_count or 0,
            max_retries=st.max_retries or 3
        )
        for st in db_subtasks
    ]
    
    original_graph = TaskGraph(
        id=db_graph.id,
        goal=db_graph.goal,
        subtasks=subtasks,
        status=TaskStatus.FAILED,
        created_at=db_graph.created_at.isoformat(),
        updated_at=db_graph.updated_at.isoformat()
    )
    
    failed_task = next(
        (t for t in subtasks if t.status == TaskStatus.FAILED),
        None
    )
    
    if not failed_task:
        return {"status": "no_failed_tasks"}
    
    engine = OrchestratorEngine(db_session=db)
    failure_context = {
        "failed_task": failed_task.id,
        "error": "User requested recovery"
    }
    
    new_graph = await engine.decomposer.replan(original_graph, failure_context)
    
    # We keep the original graph row but update its status and subtasks
    # Or create a completely new one?
    # The audit says: "recover_graph has a bug: it sets id=new_graph.id on the original graph row"
    # Let's just create a new graph model and return its ID.
    
    new_db_graph = TaskGraphModel(
        id=new_graph.id,
        goal=new_graph.goal,
        status=TaskStatus.PENDING.value,
        workspace_id=db_graph.workspace_id
    )
    db.add(new_db_graph)
    
    for st in new_graph.subtasks:
        new_db_subtask = SubTaskModel(
            id=st.id,
            graph_id=new_graph.id,
            title=st.title,
            description=st.description,
            agent_type=st.agent_type,
            status=st.status.value,
            dependencies=st.dependencies,
            input_data=st.input_data
        )
        db.add(new_db_subtask)
    
    await db.commit()
    
    asyncio.create_task(engine.run_graph(new_graph))
    
    return {
        "status": "recovery_started",
        "new_graph_id": new_graph.id
    }
