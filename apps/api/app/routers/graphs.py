from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
import structlog
from app.database.session import get_async_db, SessionLocal
from app.database.models import TaskGraphModel, SubTaskModel
from app.schemas.orchestrator import TaskGraph, SubTask, TaskStatus

logger = structlog.get_logger()

router = APIRouter(prefix="/graphs", tags=["graphs"])

@router.get("/{graph_id}")
async def get_graph(graph_id: str, db: AsyncSession = Depends(get_async_db)):
    """Get task graph details."""
    result = await db.execute(select(TaskGraphModel).where(TaskGraphModel.id == graph_id))
    graph = result.scalar_one_or_none()
    
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    result = await db.execute(select(SubTaskModel).where(SubTaskModel.graph_id == graph_id))
    subtasks = result.scalars().all()
    
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

@router.get("")
async def list_graphs(
    workspace_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_async_db)
):
    """List task graphs with optional filtering."""
    query = select(TaskGraphModel)
    
    if workspace_id:
        query = query.where(TaskGraphModel.workspace_id == workspace_id)
    if status:
        query = query.where(TaskGraphModel.status == status)
    
    query = query.order_by(TaskGraphModel.created_at.desc()).limit(limit)
    result = await db.execute(query)
    graphs = result.scalars().all()
    
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
