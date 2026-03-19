"""Agent namespace — ``/agent`` Socket.IO namespace.

Handles agent connections (API Key auth), game event push, and
action/speech submission.
"""

from __future__ import annotations

import logging
from typing import Any

import socketio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.agent import Agent
from app.models.game import Game
from app.models.player import GamePlayer
from app.security.auth import verify_api_key
from app.websocket.reconnection import reconnection_manager

logger = logging.getLogger(__name__)


class AgentNamespace(socketio.AsyncNamespace):
    """Socket.IO namespace for AI Agent connections (``/agent``)."""

    def __init__(self, sio: socketio.AsyncServer) -> None:
        super().__init__(namespace="/agent")
        self._sio = sio

    # ── connection lifecycle ──────────────────────────────────

    async def on_connect(self, sid: str, environ: dict, auth: dict | None = None) -> bool:
        """Authenticate agent via API Key on connect.

        Expected auth dict:
            {"api_key": "...", "game_id": "...", "agent_id": "..."}
        """
        if not auth:
            logger.warning("Agent connect without auth (sid=%s)", sid)
            return False

        api_key = auth.get("api_key")
        game_id = auth.get("game_id")

        if not api_key or not game_id:
            logger.warning("Agent connect missing api_key or game_id (sid=%s)", sid)
            return False

        # Verify API Key against DB
        async with async_session_factory() as db:
            agent = await self._verify_agent(db, api_key)
            if agent is None:
                logger.warning("Agent connect invalid API key (sid=%s)", sid)
                return False

            # Verify agent is a player in this game
            player = await self._get_player(db, game_id, agent.id)
            if player is None:
                logger.warning(
                    "Agent %s not in game %s (sid=%s)", agent.id, game_id, sid
                )
                return False

            # Save session data
            await self._sio.save_session(
                sid,
                {
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "game_id": game_id,
                    "player_id": player.id,
                    "seat": player.seat,
                    "role": player.role,
                },
                namespace="/agent",
            )

            # Join game room
            room = f"game:{game_id}"
            self._sio.enter_room(sid, room, namespace="/agent")

            logger.info(
                "Agent %s (seat %d) connected to game %s (sid=%s)",
                agent.name, player.seat, game_id, sid,
            )

            # Check for reconnection — flush buffered events
            reconnect_session = await reconnection_manager.on_reconnect(
                agent.id, game_id
            )
            if reconnect_session:
                # Send buffered events
                for event in reconnect_session.pending_events:
                    await self._sio.emit(
                        event.get("event_type", "game.event"),
                        event.get("data", {}),
                        room=sid,
                        namespace="/agent",
                    )

            # Send current game state sync
            game_state = await self._build_game_sync(db, game_id, player)
            await self._sio.emit("game.sync", game_state, room=sid, namespace="/agent")

        return True

    async def on_disconnect(self, sid: str) -> None:
        """Handle agent disconnection — start reconnect timer."""
        session = await self._sio.get_session(sid, namespace="/agent")
        if not session:
            return

        agent_id = session.get("agent_id")
        game_id = session.get("game_id")
        player_id = session.get("player_id")

        if agent_id and game_id and player_id:
            # Check if game is still in progress
            async with async_session_factory() as db:
                result = await db.execute(
                    select(Game).where(Game.id == game_id)
                )
                game = result.scalar_one_or_none()
                if game and game.status == "in_progress":
                    await reconnection_manager.on_disconnect(
                        agent_id, game_id, player_id, sid
                    )

            logger.info(
                "Agent %s disconnected from game %s (sid=%s)",
                agent_id, game_id, sid,
            )

    # ── client events ─────────────────────────────────────────

    async def on_agent_action(self, sid: str, data: dict[str, Any]) -> None:
        """Handle action submission from agent.

        Expected data: {"action_type": "...", "target_seat": N, "content": "..."}
        """
        session = await self._sio.get_session(sid, namespace="/agent")
        if not session:
            await self._sio.emit(
                "action.rejected",
                {"reason": "Not authenticated"},
                room=sid,
                namespace="/agent",
            )
            return

        # Acknowledge receipt
        await self._sio.emit(
            "action.ack",
            {
                "action_type": data.get("action_type"),
                "status": "received",
                "agent_id": session.get("agent_id"),
                "game_id": session.get("game_id"),
            },
            room=sid,
            namespace="/agent",
        )

        logger.info(
            "Action from agent %s in game %s: %s",
            session.get("agent_id"),
            session.get("game_id"),
            data.get("action_type"),
        )

    async def on_agent_speech(self, sid: str, data: dict[str, Any]) -> None:
        """Handle speech content from agent.

        Expected data: {"content": "..."}
        """
        session = await self._sio.get_session(sid, namespace="/agent")
        if not session:
            return

        content = data.get("content", "")
        game_id = session.get("game_id")
        seat = session.get("seat")

        # Broadcast speech to all agents in the game room
        room = f"game:{game_id}"
        await self._sio.emit(
            "player.speech",
            {
                "seat": seat,
                "content": content,
                "agent_name": session.get("agent_name"),
            },
            room=room,
            namespace="/agent",
        )

    async def on_heartbeat(self, sid: str, data: dict | None = None) -> None:
        """Handle heartbeat from agent."""
        await self._sio.emit(
            "heartbeat.ack", {"status": "ok"}, room=sid, namespace="/agent"
        )

    # ── server push helpers ───────────────────────────────────

    async def push_to_game(
        self, game_id: str, event: str, data: dict[str, Any]
    ) -> None:
        """Push an event to all agents in a game room."""
        room = f"game:{game_id}"
        await self._sio.emit(event, data, room=room, namespace="/agent")

    async def push_to_agent(
        self, sid: str, event: str, data: dict[str, Any]
    ) -> None:
        """Push an event to a specific agent by SID."""
        await self._sio.emit(event, data, room=sid, namespace="/agent")

    # ── private helpers ───────────────────────────────────────

    async def _verify_agent(
        self, db: AsyncSession, api_key: str
    ) -> Agent | None:
        """Verify API key and return the matching agent."""
        result = await db.execute(
            select(Agent).where(Agent.is_active.is_(True))
        )
        agents = result.scalars().all()
        for agent in agents:
            if verify_api_key(api_key, agent.api_key_hash):
                return agent
        return None

    async def _get_player(
        self, db: AsyncSession, game_id: str, agent_id: str
    ) -> GamePlayer | None:
        """Get the GamePlayer record for an agent in a game."""
        result = await db.execute(
            select(GamePlayer).where(
                GamePlayer.game_id == game_id,
                GamePlayer.agent_id == agent_id,
            )
        )
        return result.scalar_one_or_none()

    async def _build_game_sync(
        self, db: AsyncSession, game_id: str, player: GamePlayer
    ) -> dict[str, Any]:
        """Build a game state snapshot for sync on connect/reconnect."""
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one_or_none()
        if game is None:
            return {"error": "Game not found"}

        # Get all players
        players_result = await db.execute(
            select(GamePlayer).where(GamePlayer.game_id == game_id)
        )
        players = players_result.scalars().all()

        # Build filtered player list (only show what this agent can see)
        player_list = []
        for p in players:
            entry: dict[str, Any] = {
                "seat": p.seat,
                "is_alive": p.is_alive,
                "role": None,
            }
            # Show own role
            if p.id == player.id:
                entry["role"] = p.role
            # Werewolves see other werewolves
            elif player.role == "werewolf" and p.role == "werewolf":
                entry["role"] = p.role
            player_list.append(entry)

        return {
            "game_id": game_id,
            "status": game.status,
            "current_phase": game.current_phase,
            "current_round": game.current_round,
            "your_seat": player.seat,
            "your_role": player.role,
            "players": player_list,
        }
