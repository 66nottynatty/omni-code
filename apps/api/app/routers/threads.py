from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database.session import get_db
from ..database.models import ActionHistory, AgentLog
from ..schemas.thread import ActionHistoryResponse, AgentLogResponse, RollbackRequest
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/threads", tags=["threads"])

@router.get("/{thread_id}/history", response_model=List[ActionHistoryResponse])
async def get_thread_history(thread_id: int, db: Session = Depends(get_db)):
    return db.query(ActionHistory).filter(ActionHistory.thread_id == thread_id).all()

@router.get("/{thread_id}/logs/sse")
async def stream_thread_logs(thread_id: int):
    # SSE placeholder
    pass

@router.post("/api/rollback/{action_id}")
async def rollback_action(action_id: int, rollback: RollbackRequest, db: Session = Depends(get_db)):
    action = db.query(ActionHistory).get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    # Logic to actually revert the file change or command outcome
    # For now just update status/record
    return {"status": "success", "message": f"Action {action_id} rolled back"}
