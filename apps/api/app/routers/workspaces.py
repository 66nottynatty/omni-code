from fastapi import APIRouter
from typing import List

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

@router.get("/{workspace_id}/analysis")
async def analyze_workspace(workspace_id: int):
    return {
        "tech_stack": ["FastAPI", "Next.js", "PostgreSQL"],
        "main_language": "Python",
        "complexity": "medium"
    }
