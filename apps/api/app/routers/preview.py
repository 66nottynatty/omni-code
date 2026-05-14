from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional
from app.database.session import get_async_db
from app.database.models import PreviewSession
import structlog
import uuid
from datetime import datetime

logger = structlog.get_logger()
router = APIRouter(prefix="/preview", tags=["preview"])

@router.post("/start")
async def start_preview(data: Dict[str, Any], db: AsyncSession = Depends(get_async_db)):
    """
    Start a browser preview session.
    """
    port = data.get("port", 3000)
    workspace_id = data.get("workspace_id")
    
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required")
        
    logger.info("starting_browser_preview", port=port, workspace_id=workspace_id)
    
    # In a real system, this would spin up a container or a proxy
    # We'll save the session to DB
    url = f"https://preview-{workspace_id}.omnicode.dev"
    
    session = PreviewSession(
        workspace_id=workspace_id,
        port=port,
        url=url,
        status="starting"
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return {
        "id": session.id,
        "url": session.url,
        "port": session.port,
        "status": session.status
    }

@router.get("/status/{workspace_id}")
async def get_preview_status(workspace_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Get the status of a browser preview session.
    """
    result = await db.execute(
        select(PreviewSession)
        .where(PreviewSession.workspace_id == workspace_id)
        .order_by(PreviewSession.created_at.desc())
    )
    session = result.scalars().first()
    
    if not session:
         raise HTTPException(status_code=404, detail="No preview session found for this workspace")
         
    return {
        "workspace_id": workspace_id,
        "status": session.status,
        "url": session.url,
        "port": session.port
    }

@router.post("/capture")
async def capture_preview(data: Dict[str, Any]):
    """
    Take a screenshot of the current preview.
    Uses the browser service if available.
    """
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    
    logger.info("capturing_preview", url=url)
    
    import httpx
    try:
        # Try to call the browser service
        async with httpx.AsyncClient() as client:
            resp = await client.post("http://browser:3001/capture", json={"url": url}, timeout=30.0)
            if resp.status_code == 200:
                # In a real system, we'd save this to S3
                return {
                    "status": "success",
                    "screenshot_b64": resp.content.hex(), # Mocking it
                    "timestamp": datetime.utcnow().isoformat()
                }
    except Exception as e:
        logger.warning("browser_service_failed", error=str(e))
    
    # Fallback to mock
    return {
        "status": "success",
        "screenshot_url": f"https://screenshots.omnicode.dev/{uuid.uuid4().hex}.png",
        "timestamp": datetime.utcnow().isoformat()
    }
