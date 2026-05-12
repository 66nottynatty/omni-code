"""
Thread and action history schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ThreadCreate(BaseModel):
    """Schema for creating a new thread."""
    workspace_id: int = Field(..., description="ID of the workspace")
    title: str = Field(..., min_length=1, max_length=255, description="Thread title")


class ThreadResponse(BaseModel):
    """Schema for thread responses."""
    id: int
    workspace_id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    thread_id: int = Field(..., description="ID of the thread")
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class MessageResponse(BaseModel):
    """Schema for message responses."""
    id: int
    thread_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ActionHistoryResponse(BaseModel):
    """Schema for action history responses."""
    id: int
    thread_id: int
    action_type: str
    file_path: Optional[str] = None
    content_before: Optional[str] = None
    content_after: Optional[str] = None
    command: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentLogResponse(BaseModel):
    """Schema for agent log responses."""
    id: int
    thread_id: int
    content: str
    type: str
    created_at: datetime

    class Config:
        from_attributes = True


class RollbackRequest(BaseModel):
    """Schema for rollback requests."""
    action_id: int = Field(..., description="ID of the action to rollback")
    reason: Optional[str] = Field(None, description="Reason for rollback")