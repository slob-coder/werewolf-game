"""Schemas for Server Exception management API."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------


class ExceptionResponse(BaseModel):
    """Single exception response."""

    id: str
    exception_type: str
    exception_message: str
    exception_traceback: Optional[str] = None
    
    # Request context
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    request_params: Optional[dict[str, Any]] = None
    
    # Game context
    room_id: Optional[str] = None
    game_id: Optional[str] = None
    
    # Additional context
    context: Optional[dict[str, Any]] = None
    
    # Resolution tracking
    resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None
    
    # Metadata
    created_at: datetime

    class Config:
        from_attributes = True


class ExceptionListResponse(BaseModel):
    """Response for exceptions query."""

    total: int = Field(..., description="Total matching exceptions")
    exceptions: list[ExceptionResponse] = Field(..., description="Exception list")


class ExceptionStatsResponse(BaseModel):
    """Response for exception statistics."""

    total_exceptions: int = Field(..., description="Total exception count")
    by_type: dict[str, int] = Field(..., description="Count by exception type")
    unresolved: int = Field(..., description="Unresolved exception count")
    recent_exceptions: int = Field(..., description="Exception count in last 24h")


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class ResolveExceptionRequest(BaseModel):
    """Request to mark an exception as resolved."""

    note: str = Field(..., description="Resolution note describing how the issue was fixed")


class ResolveExceptionResponse(BaseModel):
    """Response after marking exception as resolved."""

    status: str = Field(default="ok")
    exception: ExceptionResponse
