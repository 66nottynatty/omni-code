"""Pydantic schemas for Skill management."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SkillCategory(str, Enum):
    PYTHON = "Python"
    FRONTEND = "Frontend"
    BACKEND = "Backend"
    DATABASE = "Database"
    TESTING = "Testing"
    SECURITY = "Security"
    ENGINEERING = "Engineering"
    API = "API"
    DEVOPS = "DevOps"
    DOCUMENTATION = "Documentation"
    PERFORMANCE = "Performance"
    GENERAL = "General"


class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    content: str = Field(...)
    category: str = Field(default="general")
    skill_type: str = Field(default="general")
    compatibilities: List[str] = Field(default_factory=list)
    workspace_id: Optional[int] = None
    is_global: bool = Field(default=False)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "custom_skill",
                "description": "A custom skill for this workspace",
                "content": "# Custom Skill\n\nDetailed content...",
                "category": "Engineering",
                "skill_type": "workflow",
                "compatibilities": ["warp"],
                "workspace_id": 1,
                "is_global": False
            }
        }
    }


class SkillUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    category: Optional[str] = None
    skill_type: Optional[str] = None
    compatibilities: Optional[List[str]] = None


class SkillResponse(BaseModel):
    id: int
    name: str
    description: str
    content: str
    category: str
    skill_type: str
    compatibilities: List[str]
    workspace_id: Optional[int]
    is_global: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SkillSummary(BaseModel):
    id: int
    name: str
    description: str
    category: str
    skill_type: str
    compatibilities: List[str]
    is_global: bool
    workspace_id: Optional[int]

    model_config = {"from_attributes": True}


class SkillSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    workspace_id: Optional[int] = None
    limit: int = Field(default=3, ge=1, le=10)


class SkillSearchResponse(BaseModel):
    skills: List[SkillSummary]
    query: str


class WorkspaceAnalysisResponse(BaseModel):
    tech_stack: dict
    dependencies: dict
    file_structure: List[str]
    architecture: dict
    config_files: List[str]
