"""Pydantic schemas for spectator and replay endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SpectatorPlayerState(BaseModel):
    """Player state visible to spectators."""

    seat: int
    is_alive: bool
    role: str | None = None
    death_round: int | None = None
    death_cause: str | None = None


class SpectatorSnapshot(BaseModel):
    """Live spectator snapshot of a game."""

    game_id: str
    status: str
    current_phase: str | None = None
    current_round: int
    started_at: str | None = None
    finished_at: str | None = None
    winner: str | None = None
    players: list[SpectatorPlayerState]
    recent_events: list[dict[str, Any]]


class ReplayResponse(BaseModel):
    """Full replay data for a finished game."""

    game_id: str
    events: list[dict[str, Any]]
    players: list[dict[str, Any]]
    winner: str | None = None
    rounds_played: int
    started_at: str | None = None
    finished_at: str | None = None
