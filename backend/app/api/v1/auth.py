"""API v1 router — Authentication, user, and agent management endpoints."""

import base64
import io
import random
import secrets
import string
import time
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from app.dependencies import get_current_user, get_db
from app.models.access_key import AccessKey
from app.models.agent import Agent
from app.models.user import User
from app.schemas.auth import (
    AccessKeyCreateRequest,
    AccessKeyCreateResponse,
    AccessKeyResponse,
    AccessTokenByAccessKeyRequest,
    AgentCreateRequest,
    AgentCreateResponse,
    AgentResponse,
    CaptchaResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserRegisterResponse,
    UserResponse,
)
from app.security.auth import (
    create_access_token,
    hash_api_key,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/v1", tags=["auth"])

# ── Captcha storage (in-memory, production should use Redis) ───────

_captcha_store: dict[str, tuple[str, float]] = {}  # captcha_id -> (code, expire_time)


# ── Captcha ────────────────────────────────────────────────────────


@router.get("/auth/captcha", response_model=CaptchaResponse)
async def get_captcha():
    """Generate a captcha image for registration."""
    captcha_id = str(uuid4())
    code = "".join(random.choices(string.digits, k=4))
    _captcha_store[captcha_id] = (code, time.time() + 300)  # 5 minutes expiry

    # Generate simple captcha image
    try:
        from PIL import Image, ImageDraw, ImageFont

        width, height = 120, 40
        img = Image.new("RGB", (width, height), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)

        # Draw noise lines
        for _ in range(4):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=1)

        # Draw captcha text
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except Exception:
            font = ImageFont.load_default()

        # Draw each character with slight offset
        for i, char in enumerate(code):
            x = 20 + i * 22 + random.randint(-3, 3)
            y = 8 + random.randint(-2, 2)
            draw.text((x, y), char, fill=(30, 30, 30), font=font)

        # Draw noise dots
        for _ in range(20):
            x = random.randint(0, width)
            y = random.randint(0, height)
            draw.point((x, y), fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)))

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        return CaptchaResponse(
            captcha_id=captcha_id,
            captcha_image=f"data:image/png;base64,{img_base64}",
        )
    except ImportError:
        # Fallback: return code directly (for dev without PIL)
        return CaptchaResponse(
            captcha_id=captcha_id,
            captcha_image=f"data:text/plain;base64,{base64.b64encode(code.encode()).decode()}",
        )


# ── Access Key ────────────────────────────────────────────────────

ACCESS_KEY_PREFIX = "ak_"


def generate_access_key() -> str:
    """Generate a new access key with ak_ prefix."""
    return ACCESS_KEY_PREFIX + secrets.token_urlsafe(24)


# ── User auth ────────────────────────────────────────────────────


@router.post("/auth/register", response_model=UserRegisterResponse, status_code=201)
async def register(body: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account and create first access key."""
    # Verify captcha
    stored = _captcha_store.get(body.captcha_id)
    if stored is None:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")
    code, expire_time = stored
    if time.time() > expire_time:
        del _captcha_store[body.captcha_id]
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="验证码已过期")
    if code != body.captcha_code:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="验证码错误")
    # One-time use
    del _captcha_store[body.captcha_id]

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

    # Create first access key
    raw_key = generate_access_key()
    access_key = AccessKey(
        user_id=user.id,
        name="Default",
        key_hash=hash_api_key(raw_key),
    )
    db.add(access_key)
    await db.flush()

    return UserRegisterResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        access_key=raw_key,
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with username/password and receive a JWT access token."""
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid credentials")

    token = create_access_token(data={"sub": user.id, "username": user.username})
    return TokenResponse(access_token=token)


@router.post("/auth/token-by-access-key", response_model=TokenResponse)
async def token_by_access_key(
    body: AccessTokenByAccessKeyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange an access key for a JWT token (for CLI authentication)."""
    # Validate key format
    if not body.access_key.startswith(ACCESS_KEY_PREFIX):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid access key format")

    # Find the access key
    key_hash = hash_api_key(body.access_key)
    result = await db.execute(
        select(AccessKey).where(AccessKey.key_hash == key_hash, AccessKey.is_active.is_(True))
    )
    access_key = result.scalar_one_or_none()

    if access_key is None:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid or revoked access key")

    # Get user
    user_result = await db.execute(select(User).where(User.id == access_key.user_id))
    user = user_result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

    # Update last_used_at
    access_key.last_used_at = datetime.utcnow()
    await db.flush()

    # Create JWT
    token = create_access_token(data={"sub": user.id, "username": user.username})
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return current_user


# ── Access Key management ────────────────────────────────────────


@router.get("/access-keys", response_model=list[AccessKeyResponse])
async def list_access_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all access keys for the current user."""
    result = await db.execute(
        select(AccessKey)
        .where(AccessKey.user_id == current_user.id)
        .order_by(AccessKey.created_at.desc())
    )
    return result.scalars().all()


@router.post("/access-keys", response_model=AccessKeyCreateResponse, status_code=201)
async def create_access_key(
    body: AccessKeyCreateRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new access key."""
    raw_key = generate_access_key()
    access_key = AccessKey(
        user_id=current_user.id,
        name=body.name if body else None,
        key_hash=hash_api_key(raw_key),
    )
    db.add(access_key)
    await db.flush()
    await db.refresh(access_key)

    return AccessKeyCreateResponse(
        id=access_key.id,
        name=access_key.name,
        is_active=access_key.is_active,
        last_used_at=access_key.last_used_at,
        created_at=access_key.created_at,
        key=raw_key,
    )


@router.delete("/access-keys/{key_id}", status_code=204)
async def revoke_access_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an access key (soft delete by setting is_active=False)."""
    result = await db.execute(
        select(AccessKey).where(AccessKey.id == key_id, AccessKey.user_id == current_user.id)
    )
    access_key = result.scalar_one_or_none()
    if access_key is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Access key not found")

    access_key.is_active = False
    await db.flush()


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


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific agent by ID."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.owner_id == current_user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


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
