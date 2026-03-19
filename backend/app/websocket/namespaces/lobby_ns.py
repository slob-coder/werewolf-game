"""Lobby namespace — ``/lobby`` Socket.IO namespace.

Provides real-time room list updates. No authentication required.
"""

from __future__ import annotations

import logging
from typing import Any

import socketio

logger = logging.getLogger(__name__)


class LobbyNamespace(socketio.AsyncNamespace):
    """Socket.IO namespace for the lobby (``/lobby``).

    Broadcasts room creation, deletion, status changes, and
    player count updates to all connected lobby clients.
    """

    def __init__(self, sio: socketio.AsyncServer) -> None:
        super().__init__(namespace="/lobby")
        self._sio = sio

    # ── connection lifecycle ──────────────────────────────────

    async def on_connect(self, sid: str, environ: dict, auth: dict | None = None) -> bool:
        """Accept all lobby connections (no auth required)."""
        self._sio.enter_room(sid, "lobby", namespace="/lobby")
        logger.info("Lobby client connected (sid=%s)", sid)
        return True

    async def on_disconnect(self, sid: str) -> None:
        """Handle lobby client disconnection."""
        logger.debug("Lobby client disconnected (sid=%s)", sid)

    # ── server push helpers ───────────────────────────────────

    async def push_room_update(
        self, event_type: str, data: dict[str, Any]
    ) -> None:
        """Push a room update event to all lobby clients.

        event_type examples:
            room.created, room.deleted, room.status_changed,
            room.player_joined, room.player_left
        """
        await self._sio.emit(
            event_type, data, room="lobby", namespace="/lobby"
        )
