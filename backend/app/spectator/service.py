"""SpectatorService — live spectator data and game snapshots.

Provides filtered game state for spectators (god-view or delayed public
view), augmenting the existing replay and stats modules.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import GameEvent
from app.models.game import Game
from app.models.player import GamePlayer

logger = logging.getLogger(__name__)


class SpectatorService:
    """Builds live spectator snapshots for ongoing games."""

    async def get_spectate_snapshot(
        self,
        db: AsyncSession,
        game_id: str,
        *,
        god_view: bool = False,
    ) -> dict[str, Any] | None:
        """Return a spectator-friendly snapshot of the current game state.

        Parameters
        ----------
        db:
            Async database session.
        game_id:
            The game to snapshot.
        god_view:
            If True, include full role information (for privileged
            spectators / replay).  Otherwise roles are hidden for
            alive players.
        """
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one_or_none()
        if game is None:
            return None

        # Players
        players_result = await db.execute(
            select(GamePlayer).where(GamePlayer.game_id == game_id)
        )
        players = players_result.scalars().all()

        player_list: list[dict[str, Any]] = []
        for p in players:
            entry: dict[str, Any] = {
                "seat": p.seat,
                "is_alive": p.is_alive,
                "death_round": p.death_round,
                "death_cause": p.death_cause,
            }
            if god_view or not p.is_alive:
                entry["role"] = p.role
            else:
                entry["role"] = None
            player_list.append(entry)

        # Recent public events (last 20)
        events_result = await db.execute(
            select(GameEvent)
            .where(
                GameEvent.game_id == game_id,
                GameEvent.visibility == "public",
            )
            .order_by(GameEvent.timestamp.desc())
            .limit(20)
        )
        events = events_result.scalars().all()
        event_list = [
            {
                "event_type": ev.event_type,
                "round": ev.round,
                "phase": ev.phase,
                "data": ev.data,
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
            }
            for ev in reversed(events)  # chronological order
        ]

        return {
            "game_id": game_id,
            "status": game.status,
            "current_phase": game.current_phase,
            "current_round": game.current_round,
            "started_at": game.started_at.isoformat() if game.started_at else None,
            "finished_at": game.finished_at.isoformat() if game.finished_at else None,
            "winner": game.winner,
            "players": player_list,
            "recent_events": event_list,
        }


# Singleton
spectator_service = SpectatorService()
