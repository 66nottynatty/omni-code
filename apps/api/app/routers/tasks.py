from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.schemas.orchestrator import Task
from app.database.session import get_db
from sqlalchemy.orm import Session
from app.orchestrator.models import Task as TaskModel

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=List[Task])
async def list_tasks(db: Session = Depends(get_db)):
    return db.query(TaskModel).all()

@router.post("/{task_id}/blockers/resolve")
async def resolve_blocker(task_id: str, resolution: str, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.blockers = [b for b in task.blockers if b.get("status") != "active"]
    db.commit()
    return {"status": "resolved"}
