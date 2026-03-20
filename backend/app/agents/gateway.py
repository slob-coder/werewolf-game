"""AgentGateway — manages Agent lifecycle, online status, and statistics.

Tracks connected agents, updates ``last_seen`` timestamps, and maintains
per-agent game stats (games_played, games_won).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent

logger = logging.getLogger(__name__)


class AgentGateway:
    """Coordinates agent connections across the platform.

    Maintains an in-memory set of online agents and provides helpers
    to update persistent statistics after a game ends.
    """

    def __init__(self) -> None:
        # agent_id → set of game_ids the agent is currently connected to
        self._online: dict[str, set[str]] = {}

    # ── Connection tracking ───────────────────────────────────

    async def on_connect(
        self, db: AsyncSession, agent_id: str, game_id: str
    ) -> None:
        """Record that an agent connected to a game."""
        self._online.setdefault(agent_id, set()).add(game_id)
        await self._touch_last_seen(db, agent_id)
        logger.debug("Agent %s connected to game %s", agent_id, game_id)

    async def on_disconnect(
        self, db: AsyncSession, agent_id: str, game_id: str
    ) -> None:
        """Record that an agent disconnected from a game."""
        games = self._online.get(agent_id)
        if games:
            games.discard(game_id)
            if not games:
                del self._online[agent_id]
        await self._touch_last_seen(db, agent_id)
        logger.debug("Agent %s disconnected from game %s", agent_id, game_id)

    def is_online(self, agent_id: str) -> bool:
        """Check if an agent has any active connections."""
        return bool(self._online.get(agent_id))

    def online_agents(self) -> list[str]:
        """Return list of currently online agent IDs."""
        return [aid for aid, games in self._online.items() if games]

    @property
    def online_count(self) -> int:
        return sum(1 for g in self._online.values() if g)

    # ── Statistics ────────────────────────────────────────────

    async def record_game_result(
        self,
        db: AsyncSession,
        agent_id: str,
        won: bool,
    ) -> None:
        """Increment games_played (and games_won if applicable) for an agent."""
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            logger.warning("record_game_result: agent %s not found", agent_id)
            return

        agent.games_played = (agent.games_played or 0) + 1
        if won:
            agent.games_won = (agent.games_won or 0) + 1
        agent.last_seen = datetime.now(timezone.utc)

    async def bulk_record_game_results(
        self,
        db: AsyncSession,
        results: list[dict[str, Any]],
    ) -> None:
        """Record game results for multiple agents.

        Each entry: ``{"agent_id": str, "won": bool}``
        """
        for entry in results:
            await self.record_game_result(
                db, entry["agent_id"], entry["won"]
            )

    # ── Helpers ───────────────────────────────────────────────

    async def _touch_last_seen(
        self, db: AsyncSession, agent_id: str
    ) -> None:
        """Update the last_seen timestamp for an agent."""
        await db.execute(
            update(Agent)
            .where(Agent.id == agent_id)
            .values(last_seen=datetime.now(timezone.utc))
        )

    async def get_agent_stats(
        self, db: AsyncSession, agent_id: str
    ) -> dict[str, Any] | None:
        """Return public stats for an agent."""
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            return None

        games_played = agent.games_played or 0
        games_won = agent.games_won or 0
        win_rate = (games_won / games_played * 100) if games_played > 0 else 0.0

        return {
            "agent_id": agent.id,
            "name": agent.name,
            "games_played": games_played,
            "games_won": games_won,
            "win_rate": round(win_rate, 1),
            "is_online": self.is_online(agent_id),
            "last_seen": agent.last_seen.isoformat() if agent.last_seen else None,
        }


# Singleton
agent_gateway = AgentGateway()
