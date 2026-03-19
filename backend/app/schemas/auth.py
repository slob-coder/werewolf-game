"""Pydantic schemas for authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Request schemas ──────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    email: str | None = Field(None, max_length=200)


class UserLoginRequest(BaseModel):
    username: str
    password: str


# ── Response schemas ─────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str | None = None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Agent schemas ────────────────────────────────────────────────

class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    games_played: int
    games_won: int

    model_config = {"from_attributes": True}


class AgentCreateResponse(AgentResponse):
    """Returned only on creation — includes the raw API key (shown once)."""
    api_key: str
