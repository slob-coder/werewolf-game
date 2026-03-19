"""API v1 router — Authentication, user, and agent management endpoints."""

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from app.dependencies import get_current_user, get_db
from app.models.agent import Agent
from app.models.user import User
from app.schemas.auth import (
    AgentCreateRequest,
    AgentCreateResponse,
    AgentResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.security.auth import (
    create_access_token,
    hash_api_key,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/v1", tags=["auth"])


# ── User auth ────────────────────────────────────────────────────


@router.post("/auth/register", response_model=UserResponse, status_code=201)
async def register(body: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    # Check for existing username
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Username already taken")

    # Check for existing email (if provided)
    if body.email:
        existing_email = await db.execute(select(User).where(User.email == body.email))
        if existing_email.scalar_one_or_none() is not None:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with username/password and receive a JWT access token."""
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid credentials")

    token = create_access_token(data={"sub": user.id, "username": user.username})
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return current_user


# ── Agent management ────────────────────────────────────────────


@router.post("/agents", response_model=AgentCreateResponse, status_code=201)
async def create_agent(
    body: AgentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new AI Agent and return its API key (shown only once)."""
    raw_key = secrets.token_urlsafe(32)

    agent = Agent(
        name=body.name,
        description=body.description,
        api_key_hash=hash_api_key(raw_key),
        owner_id=current_user.id,
    )
    db.add(agent)
    await db.flush()
    await db.refresh(agent)

    return AgentCreateResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        is_active=agent.is_active,
        created_at=agent.created_at,
        games_played=agent.games_played,
        games_won=agent.games_won,
        api_key=raw_key,
    )


@router.get("/agents", response_model=list[AgentResponse])
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all agents owned by the current user."""
    result = await db.execute(
        select(Agent)
        .where(Agent.owner_id == current_user.id, Agent.is_active.is_(True))
        .order_by(Agent.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an agent (set is_active=False). Only the owner can delete."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.owner_id == current_user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Agent not found")

    agent.is_active = False
    await db.flush()
