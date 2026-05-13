from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/preview", tags=["preview"])

@router.post("/start")
async def start_preview(data: Dict[str, Any]):
    """
    Start a browser preview session.
    """
    port = data.get("port", 3000)
    workspace_id = data.get("workspace_id")
    
    logger.info("starting_browser_preview", port=port, workspace_id=workspace_id)
    
    # In a real system, this would spin up a container or a proxy
    # For now, return a mock URL
    return {
        "url": f"https://preview-{workspace_id}.omnicode.dev",
        "port": port,
        "status": "starting"
    }

@router.get("/status/{workspace_id}")
async def get_preview_status(workspace_id: str):
    """
    Get the status of a browser preview session.
    """
    return {
        "workspace_id": workspace_id,
        "status": "running",
        "url": f"https://preview-{workspace_id}.omnicode.dev"
    }
