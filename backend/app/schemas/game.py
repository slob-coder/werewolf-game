"""Pydantic schemas for game operation endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Request schemas ──────────────────────────────────────────────


class ActionRequest(BaseModel):
    action_type: str = Field(..., description="Action type (e.g., werewolf_kill, vote)")
    target_seat: int | None = Field(None, description="Target seat number")
    content: str | None = Field(None, max_length=2000, description="Speech/chat content")


# ── Response schemas ─────────────────────────────────────────────


class ActionResponse(BaseModel):
    success: bool
    action_id: str | None = None
    message: str


class PlayerStateResponse(BaseModel):
    seat: int
    agent_name: str | None = None
    is_alive: bool
    role: str | None = None  # Only visible based on information filter


class GameStateResponse(BaseModel):
    game_id: str
    room_id: str
    status: str
    current_phase: str | None = None
    current_round: int
    my_seat: int | None = None
    my_role: str | None = None
    players: list[PlayerStateResponse]
    started_at: datetime
    finished_at: datetime | None = None
    winner: str | None = None


class GameEventResponse(BaseModel):
    id: str
    event_type: str
    round: int
    phase: str
    data: dict
    visibility: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class GameEventsListResponse(BaseModel):
    game_id: str
    events: list[GameEventResponse]
