"""
Base schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Generic, TypeVar
from datetime import datetime


T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum items to return")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response structure."""
    items: list[T]
    total: int
    skip: int
    limit: int


class TimestampMixin(BaseModel):
    """Add created_at and updated_at to models."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(description="Overall health status")
    db: str = Field(description="Database connection status")
    redis: str = Field(description="Redis connection status")
    db_latency_ms: Optional[float] = Field(default=None, description="Database latency in milliseconds")
    redis_latency_ms: Optional[float] = Field(default=None, description="Redis latency in milliseconds")


class ErrorDetail(BaseModel):
    """Structured error detail."""
    code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    details: Optional[dict] = Field(default=None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response structure."""
    error: ErrorDetail
    meta: dict = Field(default_factory=dict)


class SuccessResponse(BaseModel):
    """Standard success response."""
    status: str = Field(default="success")
    message: Optional[str] = None
    data: Optional[dict] = None