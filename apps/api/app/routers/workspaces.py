from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..database.models import Workspace
from ..intelligence.workspace_analyzer import WorkspaceAnalyzer
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])

@router.post("/{workspace_id}/generate-skill")
async def generate_workspace_skill(workspace_id: int, db: Session = Depends(get_db)):
    workspace = db.query(Workspace).get(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    # Trigger async skill generation
    return {"status": "success", "message": "Skill generation started"}

@router.get("/{workspace_id}/analyze")
async def analyze_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace = db.query(Workspace).get(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    analyzer = WorkspaceAnalyzer()
    # Mock analysis result
    return {
        "tech_stack": {"backend": "FastAPI", "frontend": "Next.js"},
        "dependencies": {},
        "file_structure": ["apps/", "packages/"],
        "architecture": "Monorepo",
        "config_files": ["package.json", "requirements.txt"]
    }
