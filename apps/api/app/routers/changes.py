from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import List
from app.database.session import get_async_db
from app.database.models import PendingChange, Thread, Workspace
import structlog
import os
import anyio

logger = structlog.get_logger()

# Align with SDK which uses /api/pending-changes
router = APIRouter(prefix="/pending-changes", tags=["changes"])

@router.get("/{thread_id}")
async def get_changes(thread_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(PendingChange).where(PendingChange.thread_id == thread_id))
    return result.scalars().all()

@router.post("/{change_id}/accept")
async def accept_change(change_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(PendingChange)
        .options(joinedload(PendingChange.thread).joinedload(Thread.workspace))
        .where(PendingChange.id == change_id)
    )
    change = result.scalar_one_or_none()
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    
    if change.status == "accepted":
        return {"status": "accepted", "file_path": change.file_path, "message": "Already accepted"}

    try:
        # Determine workspace path
        workspace = change.thread.workspace
        repo_path = f"/workspace/{workspace.owner}/{workspace.repo}"
        if not os.path.exists(repo_path):
            repo_path = "/home/engine/project"

        full_path = os.path.join(repo_path, change.file_path.lstrip("/"))
        
        # Check if file is within repo_path for security
        real_path = os.path.realpath(full_path)
        if not real_path.startswith(os.path.realpath(repo_path)):
            raise HTTPException(status_code=403, detail="Invalid file path")

        # Apply the change (using new_content)
        async def write_file():
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            content_to_write = change.new_content if change.new_content is not None else change.diff
            with open(full_path, "w") as f:
                f.write(content_to_write)
        
        await anyio.to_thread.run_sync(write_file)

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
