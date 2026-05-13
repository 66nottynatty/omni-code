from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database.session import get_async_db
from app.database.models import Workspace, CodeChunk
from sqlalchemy import func

from app.utils.project_config import get_project_config
import os

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

@router.get("", response_model=List[dict])
async def list_workspaces(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Workspace))
    workspaces = result.scalars().all()
    return [
        {
            "id": w.id,
            "owner": w.owner,
            "repo": w.repo,
            "branch": w.branch,
            "created_at": w.created_at
        }
        for w in workspaces
    ]

@router.get("/{workspace_id}/config")
async def get_workspace_config(workspace_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # In a real system, we'd have the path where the repo is cloned
    repo_path = f"/workspace/{workspace.owner}/{workspace.repo}"
    # Fallback to current project directory for development
    if not os.path.exists(repo_path):
         repo_path = "/home/engine/project"
         
    return get_project_config(repo_path)

# SDK uses /api/workspaces/{id}/analyze
@router.get("/{workspace_id}/analyze")
async def analyze_workspace(workspace_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(CodeChunk.chunk_type, func.count(CodeChunk.id))
        .where(CodeChunk.workspace_id == workspace_id)
        .group_by(CodeChunk.chunk_type)
    )
    stats = dict(result.all())
    
    return {
        "workspace_id": workspace_id,
        "stats": stats,
        "main_language": "Python" if stats.get("function", 0) > 0 else "Unknown",
        "complexity": "medium" if sum(stats.values()) > 100 else "low"
    }

@router.post("/{workspace_id}/generate-skill")
async def generate_skill(workspace_id: int, db: AsyncSession = Depends(get_async_db)):
    from app.database.models import BackgroundTask
    
    # Create a background task for skill generation
    task = BackgroundTask(
        workspace_id=workspace_id,
        task_type="skill_generation",
        status="pending",
        payload={"workspace_id": workspace_id}
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    return {
        "status": "success", 
        "message": "Skill generation task created",
        "task_id": task.id
    }
