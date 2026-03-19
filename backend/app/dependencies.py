"""FastAPI dependencies — DB session, current user, current agent."""

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from app.database import async_session_factory
from app.models.agent import Agent
from app.models.user import User
from app.security.auth import decode_access_token, verify_api_key
from app.security.rate_limiter import rate_limiter

bearer_scheme = HTTPBearer(auto_error=False)

API_KEY_HEADER = "X-Agent-Key"


# ── Database session ──────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for request handlers."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── JWT authentication (users) ───────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the JWT Bearer token, returning the User."""
    if credentials is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


# ── API Key authentication (agents) ─────────────────────────────

async def get_current_agent(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """Validate X-Agent-Key header, apply rate limiting, and return the Agent."""
    api_key = request.headers.get(API_KEY_HEADER)
    if not api_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Missing X-Agent-Key header",
        )

    # Rate-limit by raw key prefix (first 16 chars for privacy)
    await rate_limiter.check(request, key=f"agent:{api_key[:16]}")

    # Scan agents — in production you'd index a key prefix for O(1) lookup.
    # For now, fetch active agents and verify bcrypt hash.
    result = await db.execute(select(Agent).where(Agent.is_active.is_(True)))
    agents = result.scalars().all()

    for agent in agents:
        if verify_api_key(api_key, agent.api_key_hash):
            return agent

    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail="Invalid API key",
    )
