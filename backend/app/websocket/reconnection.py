"""Reconnection manager — handles agent disconnect/reconnect during games.

Keeps session state for a configurable window so agents can reconnect
and resume from where they left off.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_RECONNECT_TIMEOUT = 60  # seconds


@dataclass
class DisconnectedSession:
    """State preserved for a disconnected agent."""

    agent_id: str
    game_id: str
    player_id: str
    sid: str  # original socket id
    disconnected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    pending_events: list[dict[str, Any]] = field(default_factory=list)
    timeout_task: asyncio.Task[None] | None = field(default=None, repr=False)


class ReconnectionManager:
    """Manages agent disconnection and reconnection during games.

    When an agent disconnects:
    1. Session state is preserved in memory
    2. Pending events are buffered
    3. A timeout timer starts

    When the agent reconnects within the window:
    1. Buffered events are flushed to the new connection
    2. Current game state snapshot is sent
    3. Timer is cancelled

    If timeout expires:
    1. Agent is marked offline
    2. Timeout callback is fired (for auto-action handling)
    """

    def __init__(self, timeout_seconds: int = DEFAULT_RECONNECT_TIMEOUT) -> None:
        self._timeout_seconds = timeout_seconds
        # Key: (agent_id, game_id)
        self._sessions: dict[tuple[str, str], DisconnectedSession] = {}
        self._timeout_callback: Any = None

    def set_timeout_callback(self, callback: Any) -> None:
        """Set the callback to invoke when reconnection times out.

        Signature: async def callback(agent_id: str, game_id: str) -> None
        """
        self._timeout_callback = callback

    # ── disconnect ────────────────────────────────────────────

    async def on_disconnect(
        self,
        agent_id: str,
        game_id: str,
        player_id: str,
        sid: str,
    ) -> None:
        """Record an agent disconnection and start the reconnect timer."""
        key = (agent_id, game_id)

        # Cancel any existing timer for this agent+game
        existing = self._sessions.get(key)
        if existing and existing.timeout_task and not existing.timeout_task.done():
            existing.timeout_task.cancel()

        session = DisconnectedSession(
            agent_id=agent_id,
            game_id=game_id,
            player_id=player_id,
            sid=sid,
        )

        # Start timeout timer
        session.timeout_task = asyncio.create_task(
            self._timeout_handler(agent_id, game_id),
            name=f"reconnect-timeout:{agent_id}:{game_id}",
        )

        self._sessions[key] = session
        logger.info(
            "Agent %s disconnected from game %s. Reconnect window: %ds",
            agent_id, game_id, self._timeout_seconds,
        )

    # ── reconnect ─────────────────────────────────────────────

    async def on_reconnect(
        self, agent_id: str, game_id: str
    ) -> DisconnectedSession | None:
        """Handle agent reconnection. Returns the session with buffered events,
        or None if no disconnected session exists."""
        key = (agent_id, game_id)
        session = self._sessions.pop(key, None)
        if session is None:
            return None

        # Cancel timeout
        if session.timeout_task and not session.timeout_task.done():
            session.timeout_task.cancel()

        logger.info(
            "Agent %s reconnected to game %s. Flushing %d buffered events.",
            agent_id, game_id, len(session.pending_events),
        )
        return session

    # ── buffer events ─────────────────────────────────────────

    def buffer_event(
        self, agent_id: str, game_id: str, event: dict[str, Any]
    ) -> bool:
        """Buffer an event for a disconnected agent.

        Returns True if the agent has a disconnected session and the event
        was buffered, False otherwise.
        """
        key = (agent_id, game_id)
        session = self._sessions.get(key)
        if session is None:
            return False
        session.pending_events.append(event)
        return True

    # ── queries ───────────────────────────────────────────────

    def is_disconnected(self, agent_id: str, game_id: str) -> bool:
        """Check if an agent is currently in disconnected state."""
        return (agent_id, game_id) in self._sessions

    def get_session(
        self, agent_id: str, game_id: str
    ) -> DisconnectedSession | None:
        """Get the disconnected session for an agent, if any."""
        return self._sessions.get((agent_id, game_id))

    @property
    def disconnected_count(self) -> int:
        return len(self._sessions)

    # ── cleanup ───────────────────────────────────────────────

    def cleanup_game(self, game_id: str) -> int:
        """Remove all disconnected sessions for a game. Returns count removed."""
        keys_to_remove = [k for k in self._sessions if k[1] == game_id]
        for key in keys_to_remove:
            session = self._sessions.pop(key)
            if session.timeout_task and not session.timeout_task.done():
                session.timeout_task.cancel()
        return len(keys_to_remove)

    # ── timeout handler ───────────────────────────────────────

    async def _timeout_handler(self, agent_id: str, game_id: str) -> None:
        """Wait for the reconnect window and then fire the timeout callback."""
        try:
            await asyncio.sleep(self._timeout_seconds)

            key = (agent_id, game_id)
            session = self._sessions.pop(key, None)
            if session is None:
                return  # already reconnected

            logger.warning(
                "Agent %s reconnect timeout for game %s",
                agent_id, game_id,
            )

            if self._timeout_callback:
                try:
                    await self._timeout_callback(agent_id, game_id)
                except Exception:
                    logger.exception(
                        "Error in reconnect timeout callback for agent %s",
                        agent_id,
                    )
        except asyncio.CancelledError:
            pass


# Singleton
reconnection_manager = ReconnectionManager()
