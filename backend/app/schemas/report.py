"""Schemas for Agent Observability Reports API."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class ReportPayload(BaseModel):
    """Single report payload from agent."""

    agent_id: str = Field(..., description="Agent identifier")
    report_type: str = Field(
        ..., description="Report type: exception | event | health"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    session: dict[str, Any] = Field(
        default_factory=dict, description="Session context (room_id, game_id, etc.)"
    )
    payload: dict[str, Any] = Field(..., description="Report content")


class ReportsRequest(BaseModel):
    """Batch reports request from agent."""

    agent_id: str = Field(..., description="Agent identifier (for routing)")
    reports: list[ReportPayload] = Field(..., description="List of reports")


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class ReportsResponse(BaseModel):
    """Response for batch reports submission."""

    status: str = Field(default="ok")
    received: int = Field(..., description="Number of reports received")
    stored: int = Field(..., description="Number of reports stored")


class ReportResponse(BaseModel):
    """Single report response for queries."""

    id: str
    agent_id: str
    report_type: str
    timestamp: datetime
    room_id: Optional[str] = None
    game_id: Optional[str] = None
    payload: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ReportsListResponse(BaseModel):
    """Response for reports query."""

    total: int = Field(..., description="Total matching reports")
    reports: list[ReportResponse] = Field(..., description="Report list")


class ReportsStatsResponse(BaseModel):
    """Response for reports statistics."""

    total_reports: int = Field(..., description="Total report count")
    by_type: dict[str, int] = Field(..., description="Count by report type")
    by_agent: dict[str, int] = Field(..., description="Count by agent")
    recent_errors: int = Field(..., description="Error count in last 24h")
