from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.database.session import get_async_db
from app.database.models import ActionHistory, Thread, Workspace
import os
import anyio

router = APIRouter(prefix="/rollback", tags=["rollback"])

@router.post("/{action_id}")
async def rollback_action(action_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(ActionHistory)
        .options(joinedload(ActionHistory.thread).joinedload(Thread.workspace))
        .where(ActionHistory.id == action_id)
    )
    action = result.scalar_one_or_none()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action history not found")
        
    if action.action_type != "file_edit":
         raise HTTPException(status_code=400, detail="Only file_edit actions can be rolled back")

    if not action.content_before:
         raise HTTPException(status_code=400, detail="No 'content_before' found for this action")

    # Determine workspace path
    workspace = action.thread.workspace
    repo_path = f"/workspace/{workspace.owner}/{workspace.repo}"
    if not os.path.exists(repo_path):
        repo_path = "/home/engine/project"

    full_path = os.path.join(repo_path, action.file_path.lstrip("/"))
    
    # Check if file is within repo_path for security
    real_path = os.path.realpath(full_path)
    if not real_path.startswith(os.path.realpath(repo_path)):
        raise HTTPException(status_code=403, detail="Invalid file path")

    # Apply the content_before back to the file
    try:
        async def write_file():
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(action.content_before)
        
        await anyio.to_thread.run_sync(write_file)
            
        return {
            "status": "success", 
            "reverted_file": action.file_path,
            "action_id": action_id,
            "message": f"Successfully rolled back to previous state."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollback file: {str(e)}")
