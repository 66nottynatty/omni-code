"""
Model/provider schemas for AI model selection.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class CostTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class ModelResponse(BaseModel):
    """Schema for AI model responses."""
    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Display name")
    provider: str = Field(..., description="Model provider")
    context_window: str = Field(..., description="Context window size")
    cost_tier: str = Field(..., description="Cost tier classification")

    class Config:
        from_attributes = True


class ModelSelectionCreate(BaseModel):
    """Schema for creating/updating model selection."""
    user_id: int = Field(..., description="User ID")
    provider: str = Field(..., description="Provider name")
    model_name: str = Field(..., description="Model name")


class ModelSelectionResponse(BaseModel):
    """Schema for model selection responses."""
    id: int
    user_id: int
    provider: str
    model_name: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True