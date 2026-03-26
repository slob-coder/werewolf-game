"""Pydantic schemas for room management endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Request schemas ──────────────────────────────────────────────


class RoomCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    player_count: int = Field(default=9, ge=6, le=12)
    role_preset: str | None = None
    custom_roles: dict[str, int] | None = None
    speech_timeout: int = Field(default=90, ge=10, le=300)
    action_timeout: int = Field(default=60, ge=10, le=180)
    vote_timeout: int = Field(default=60, ge=10, le=180)
    allow_spectators: bool = True
    max_spectators: int = Field(default=50, ge=0, le=200)
    auto_start: bool = True
    content_filter: bool = False


# ── Response schemas ─────────────────────────────────────────────


class PlayerSlotResponse(BaseModel):
    seat: int
    agent_id: str | None = None
    agent_name: str | None = None
    status: Literal["empty", "occupied", "ready", "disconnected"]

    model_config = {"from_attributes": True}


class RoomResponse(BaseModel):
    id: str
    name: str
    status: str
    config: dict
    created_by: str | None = None
    created_at: datetime
    player_count: int
    current_players: int
    slots: list[PlayerSlotResponse]
    current_game_id: str | None = None  # 当前进行中的游戏 ID

    model_config = {"from_attributes": True}


class RoomListResponse(BaseModel):
    id: str
    name: str
    status: str
    player_count: int
    current_players: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomJoinResponse(BaseModel):
    seat: int
    room_id: str
    agent_id: str
    message: str


class RoomReadyResponse(BaseModel):
    seat: int
    room_id: str
    is_ready: bool
    message: str


class RoomStartResponse(BaseModel):
    room_id: str
    game_id: str
    message: str
