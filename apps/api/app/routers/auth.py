from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, Dict
import structlog
from app.database.session import get_db
from app.core.security import security_manager
from app.database.models import User

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])

async def get_current_user_id(
    authorization: Optional[str] = Header(None)
) -> int:
    """Extract user ID from Authorization header."""
    if not authorization:
        return 1
    user_id = security_manager.validate_bearer_token(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return int(user_id)

@router.post("/store-token")
async def store_token(
    data: Dict[str, str],
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    github_token = data.get("github_token")
    if not github_token:
        raise HTTPException(status_code=400, detail="GitHub token required")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, username=f"user_{user_id}")
        db.add(user)
    
    encrypted = security_manager.encrypt_token(github_token)
    user.access_token_encrypted = encrypted
    db.commit()
    logger.info("token_stored", user_id=user_id)
    return {"status": "success", "message": "Token stored securely"}

@router.delete("/token")
async def delete_token(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.access_token_encrypted = None
        db.commit()
    return {"status": "success"}

@router.get("/token-status")
async def get_token_status(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    user = db.query(User).filter(User.id == user_id).first()
    return {
        "has_token": bool(user and user.access_token_encrypted),
        "token_type": "encrypted"
    }
