from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database.session import get_async_db
from app.database.models import PendingChange
import structlog

logger = structlog.get_logger()

# Align with SDK which uses /api/pending-changes
router = APIRouter(prefix="/pending-changes", tags=["changes"])

@router.get("/{thread_id}")
async def get_changes(thread_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(PendingChange).where(PendingChange.thread_id == thread_id))
    return result.scalars().all()

@router.post("/{change_id}/accept")
async def accept_change(change_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(PendingChange).where(PendingChange.id == change_id))
    change = result.scalar_one_or_none()
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    
    # In a real system, we would apply the diff to the file
    # For now, let's simulate applying it if we have the tools
    try:
        # Simple simulation: we'll mark it as accepted
        # If we had the actual file and diff application logic, we'd call it here
        change.status = "accepted"
        await db.commit()
        
        logger.info("change_accepted", change_id=change_id, file_path=change.file_path)
        return {"status": "accepted", "file_path": change.file_path}
    except Exception as e:
        logger.error("accept_change_failed", change_id=change_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{change_id}/reject")
async def reject_change(change_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(PendingChange).where(PendingChange.id == change_id))
    change = result.scalar_one_or_none()
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    
    change.status = "rejected"
    await db.commit()
    return {"status": "rejected"}
