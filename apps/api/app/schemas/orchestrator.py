from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"

class SubTask(BaseModel):
    id: str
    title: str
    description: str
    agent_type: str  # backend, frontend, devops, etc.
    model_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    cost: Optional[Dict[str, Any]] = None
    tokens_used: int = 0
    retry_count: int = 0
    max_retries: int = 3
    completed_at: Optional[str] = None

class TaskGraph(BaseModel):
    id: str
    goal: str
    subtasks: List[SubTask]
    status: TaskStatus = TaskStatus.PENDING
    created_at: str
    updated_at: str

class OrchestratorRequest(BaseModel):
    prompt: str
    workspace_id: int
    prefer_local: bool = False

class OrchestratorResponse(BaseModel):
    graph_id: str
    status: str
