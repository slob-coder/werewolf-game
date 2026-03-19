"""Spectator namespace — ``/spectator`` Socket.IO namespace.

Provides god-view real-time data to authenticated spectators.
"""

from __future__ import annotations

import logging
from typing import Any

import socketio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.game import Game
from app.models.player import GamePlayer
from app.security.auth import decode_access_token

logger = logging.getLogger(__name__)


class SpectatorNamespace(socketio.AsyncNamespace):
    """Socket.IO namespace for spectators (``/spectator``).

    Spectators see the full god-view: all roles, all actions,
    vote details, and agent reasoning chains.
    """

    def __init__(self, sio: socketio.AsyncServer) -> None:
        super().__init__(namespace="/spectator")
        self._sio = sio

    # ── connection lifecycle ──────────────────────────────────

    async def on_connect(self, sid: str, environ: dict, auth: dict | None = None) -> bool:
        """Authenticate spectator via JWT Bearer token.

        Expected auth dict:
            {"token": "...", "game_id": "..."}
        """
        if not auth:
            logger.warning("Spectator connect without auth (sid=%s)", sid)
            return False

        token = auth.get("token")
        game_id = auth.get("game_id")

        if not token or not game_id:
            logger.warning("Spectator connect missing token or game_id (sid=%s)", sid)
            return False

        # Verify JWT
        payload = decode_access_token(token)
        if payload is None:
            logger.warning("Spectator connect invalid JWT (sid=%s)", sid)
            return False

        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Spectator connect invalid JWT payload (sid=%s)", sid)
            return False

        # Save session
        await self._sio.save_session(
            sid,
            {
                "user_id": user_id,
                "game_id": game_id,
            },
            namespace="/spectator",
        )

        # Join game spectator room
        room = f"spectator:{game_id}"
        self._sio.enter_room(sid, room, namespace="/spectator")

        logger.info(
            "Spectator %s connected to game %s (sid=%s)",
            user_id, game_id, sid,
        )

        # Send full game state snapshot (god view)
        async with async_session_factory() as db:
            snapshot = await self._build_god_view(db, game_id)
            await self._sio.emit(
                "game.snapshot", snapshot, room=sid, namespace="/spectator"
            )

        return True

    async def on_disconnect(self, sid: str) -> None:
        """Handle spectator disconnection."""
        session = await self._sio.get_session(sid, namespace="/spectator")
        if session:
            logger.info(
                "Spectator %s disconnected from game %s (sid=%s)",
                session.get("user_id"),
                session.get("game_id"),
                sid,
            )

    # ── server push helpers ───────────────────────────────────

    async def push_to_game_spectators(
        self, game_id: str, event: str, data: dict[str, Any]
    ) -> None:
        """Push an event to all spectators watching a game."""
        room = f"spectator:{game_id}"
        await self._sio.emit(event, data, room=room, namespace="/spectator")

    # ── private helpers ───────────────────────────────────────

    async def _build_god_view(
        self, db: AsyncSession, game_id: str
    ) -> dict[str, Any]:
        """Build full god-view game state snapshot."""
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one_or_none()
        if game is None:
            return {"error": "Game not found"}

        players_result = await db.execute(
            select(GamePlayer).where(GamePlayer.game_id == game_id)
        )
        players = players_result.scalars().all()

        # Full visibility — show all roles
        player_list = []
        for p in players:
            player_list.append({
                "seat": p.seat,
                "agent_id": p.agent_id,
                "role": p.role,
                "is_alive": p.is_alive,
                "death_round": p.death_round,
                "death_cause": p.death_cause,
            })

        return {
            "game_id": game_id,
            "status": game.status,
            "current_phase": game.current_phase,
            "current_round": game.current_round,
            "winner": game.winner,
            "win_reason": game.win_reason,
            "role_config": game.role_config,
            "players": player_list,
        }
