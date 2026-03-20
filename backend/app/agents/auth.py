"""Agent authentication helpers.

Extracts agent-specific auth logic from the generic security module
to keep concerns separated.
"""

from __future__ import annotations

from fastapi import Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from app.models.agent import Agent
from app.security.auth import verify_api_key


async def authenticate_agent(
    db: AsyncSession,
    api_key: str,
) -> Agent:
    """Verify an API key and return the matching active Agent.

    Raises ``HTTPException(401)`` if the key is invalid or the agent
    is deactivated.
    """
    result = await db.execute(
        select(Agent).where(Agent.is_active.is_(True))
    )
    agents = result.scalars().all()

    for agent in agents:
        if verify_api_key(api_key, agent.api_key_hash):
            return agent

    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired API key",
    )


async def authenticate_agent_for_game(
    db: AsyncSession,
    api_key: str,
    game_id: str,
) -> tuple[Agent, "GamePlayer"]:  # type: ignore[name-defined]
    """Verify API key and ensure the agent is a player in the given game.

    Returns ``(agent, player)`` or raises ``HTTPException``.
    """
    from app.models.player import GamePlayer

    agent = await authenticate_agent(db, api_key)

    result = await db.execute(
        select(GamePlayer).where(
            GamePlayer.game_id == game_id,
            GamePlayer.agent_id == agent.id,
        )
    )
    player = result.scalar_one_or_none()
    if player is None:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Agent is not a player in this game",
        )

    return agent, player
