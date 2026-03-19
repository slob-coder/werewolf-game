"""Replay data generation — assembles complete game event sequences for replay.

Provides the replay data for GET /api/v1/games/{id}/replay.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action import GameAction
from app.models.event import GameEvent
from app.models.game import Game
from app.models.player import GamePlayer

logger = logging.getLogger(__name__)


async def get_replay_data(
    db: AsyncSession, game_id: str
) -> dict[str, Any] | None:
    """Build replay data for a game.

    Returns a dict with the full event sequence, player info,
    and game metadata, or None if the game doesn't exist.
    """
    # Fetch game
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if game is None:
        return None

    # Fetch players
    players_result = await db.execute(
        select(GamePlayer)
        .where(GamePlayer.game_id == game_id)
        .order_by(GamePlayer.seat)
    )
    players = players_result.scalars().all()

    # Fetch events ordered by timestamp
    events_result = await db.execute(
        select(GameEvent)
        .where(GameEvent.game_id == game_id)
        .order_by(GameEvent.timestamp)
    )
    events = events_result.scalars().all()

    # Fetch actions ordered by timestamp
    actions_result = await db.execute(
        select(GameAction)
        .where(GameAction.game_id == game_id)
        .order_by(GameAction.timestamp)
    )
    actions = actions_result.scalars().all()

    # Build player info (god view — full roles)
    player_info = [
        {
            "seat": p.seat,
            "agent_id": p.agent_id,
            "role": p.role,
            "is_alive": p.is_alive,
            "death_round": p.death_round,
            "death_cause": p.death_cause,
        }
        for p in players
    ]

    # Build event sequence
    event_sequence = [
        {
            "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
            "phase": ev.phase,
            "round": ev.round,
            "event_type": ev.event_type,
            "visibility": ev.visibility,
            "data": ev.data,
        }
        for ev in events
    ]

    # Build action sequence
    action_sequence = [
        {
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "phase": a.phase,
            "round": a.round,
            "action_type": a.action_type,
            "player_id": a.player_id,
            "target_seat": a.target_seat,
            "content": a.content,
            "is_timeout": a.is_timeout,
        }
        for a in actions
    ]

    return {
        "game_id": game_id,
        "status": game.status,
        "winner": game.winner,
        "win_reason": game.win_reason,
        "role_config": game.role_config,
        "started_at": game.started_at.isoformat() if game.started_at else None,
        "finished_at": game.finished_at.isoformat() if game.finished_at else None,
        "players": player_info,
        "events": event_sequence,
        "actions": action_sequence,
        "total_rounds": game.current_round,
    }
