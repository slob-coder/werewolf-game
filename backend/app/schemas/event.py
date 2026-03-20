"""Pydantic schemas for game event endpoints."""

from datetime import datetime

from pydantic import BaseModel


class GameEventResponse(BaseModel):
    """A single game event."""

    id: str
    event_type: str
    round: int
    phase: str
    data: dict
    visibility: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class GameEventsListResponse(BaseModel):
    """List of game events."""

    game_id: str
    events: list[GameEventResponse]
