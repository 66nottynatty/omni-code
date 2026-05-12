from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..database.models import PendingChange
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/pending-changes", tags=["changes"])

@router.post("/{change_id}/accept")
async def accept_change(change_id: int, db: Session = Depends(get_db)):
    change = db.query(PendingChange).get(change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    change.status = "accepted"
    db.commit()
    return {"status": "success"}

@router.post("/{change_id}/reject")
async def reject_change(change_id: int, db: Session = Depends(get_db)):
    change = db.query(PendingChange).get(change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    change.status = "rejected"
    db.commit()
    return {"status": "success"}
