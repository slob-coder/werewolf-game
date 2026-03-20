"""Pydantic schemas for action-related endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class ActionRequest(BaseModel):
    """Request body for submitting a game action."""

    action_type: str = Field(..., description="Action type (e.g., werewolf_kill, vote)")
    target_seat: int | None = Field(None, description="Target seat number")
    content: str | None = Field(None, max_length=2000, description="Speech/chat content")
    metadata: dict | None = Field(
        None,
        description="Optional metadata (chain_of_thought, confidence, reasoning)",
    )


class ActionResponse(BaseModel):
    """Response from an action submission."""

    success: bool
    action_id: str | None = None
    message: str


class ActionHistoryItem(BaseModel):
    """A single action in history."""

    id: str
    action_type: str
    round: int
    phase: str
    target_seat: int | None = None
    content: str | None = None
    timestamp: datetime

    model_config = {"from_attributes": True}
