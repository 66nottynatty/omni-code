from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database.session import get_db
from ..database.models import BackgroundTask, TaskLog, BlockerNotification
from ..schemas.task import TaskCreate, TaskResponse, TaskLogResponse, BlockerResolve
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.post("", response_model=TaskResponse)
async def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    task = BackgroundTask(
        workspace_id=task_in.workspace_id,
        task_type=task_in.task_type,
        payload=task_in.payload,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    workspace_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(BackgroundTask)
    if workspace_id:
        query = query.filter(BackgroundTask.workspace_id == workspace_id)
    if status:
        query = query.filter(BackgroundTask.status == status)
    return query.order_by(BackgroundTask.created_at.desc()).all()

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(BackgroundTask).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/{task_id}/resolve")
async def resolve_blocker(task_id: int, resolve_in: BlockerResolve, db: Session = Depends(get_db)):
    blocker = db.query(BlockerNotification).filter(
        BlockerNotification.task_id == task_id,
        BlockerNotification.resolved == False
    ).first()
    
    if not blocker:
        raise HTTPException(status_code=404, detail="Active blocker not found")
        
    blocker.resolved = True
    blocker.resolution = resolve_in.resolution
    
    task = db.query(BackgroundTask).get(task_id)
    if task:
        task.status = "running"
        
    db.commit()
    return {"status": "success"}

@router.get("/{task_id}/logs/sse")
async def stream_task_logs(task_id: int):
    # This should be implemented via SSE, using main.py logic as reference
    # For now, placeholder to avoid 404
    pass
