"""
Task-related schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskType(str, Enum):
    AGENT_RUN = "agent_run"
    REPO_INDEX = "repo_index"
    CODE_SEARCH = "code_search"
    EMBEDDING_UPDATE = "embedding_update"


class TaskCreate(BaseModel):
    """Schema for creating a new task."""
    workspace_id: int = Field(..., description="ID of the workspace")
    task_type: str = Field(..., description="Type of task to create")
    payload: dict = Field(default_factory=dict, description="Task payload data")


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    status: Optional[str] = Field(None, description="New status for the task")
    payload: Optional[dict] = Field(None, description="Updated payload data")


class TaskResponse(BaseModel):
    """Schema for task responses."""
    id: int
    workspace_id: int
    status: str
    task_type: str
    payload: Optional[dict] = None
    result: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskListParams(BaseModel):
    """Query parameters for listing tasks."""
    workspace_id: Optional[int] = Field(None, description="Filter by workspace")
    status: Optional[str] = Field(None, description="Filter by status")
    task_type: Optional[str] = Field(None, description="Filter by task type")


class BlockerResolve(BaseModel):
    """Schema for resolving a blocker."""
    resolution: str = Field(..., min_length=1, description="Resolution text")


class TaskLogResponse(BaseModel):
    """Schema for task log entries."""
    id: int
    task_id: int
    content: str
    level: str
    created_at: datetime

    class Config:
        from_attributes = True


class BlockerNotificationResponse(BaseModel):
    """Schema for blocker notification responses."""
    id: int
    task_id: int
    reason: str
    resolved: bool
    resolution: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True