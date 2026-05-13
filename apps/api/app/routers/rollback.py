from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_async_db
from app.database.models import ActionHistory
import os

router = APIRouter(prefix="/rollback", tags=["rollback"])

@router.post("/{action_id}")
async def rollback_action(action_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(ActionHistory).where(ActionHistory.id == action_id))
    action = result.scalar_one_or_none()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action history not found")
        
    if action.action_type != "file_edit":
         raise HTTPException(status_code=400, detail="Only file_edit actions can be rolled back")

    if not action.content_before:
         raise HTTPException(status_code=400, detail="No 'content_before' found for this action")

    # Apply the content_before back to the file
    try:
        # In this environment, we might need to resolve the path
        repo_path = "/home/engine/project" # Fallback/Default for this environment
        full_path = os.path.join(repo_path, action.file_path.lstrip("/"))
        
        with open(full_path, "w") as f:
            f.write(action.content_before)
            
        return {
            "status": "success", 
            "reverted_file": action.file_path,
            "action_id": action_id,
            "message": f"Successfully rolled back to previous state."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollback file: {str(e)}")
