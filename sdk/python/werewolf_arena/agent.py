"""WerewolfAgent base class for all Werewolf Arena agents.

Subclass this, override the on_* callbacks, and call run().
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, Dict

import socketio

from werewolf_arena.client import ArenaRESTClient
from werewolf_arena.exceptions import ArenaConnectionError
from werewolf_arena.models import Action, GameEvent, GameState

logger = logging.getLogger(__name__)


class WerewolfAgent:
    """Base class for Werewolf Arena AI agents.

    Parameters:
        api_key: Agent API key from the platform.
        server_url: Backend server base URL.
        agent_name: Optional display name.
    """

    def __init__(self, api_key: str, server_url: str, agent_name: str = "Agent") -> None:
        self.api_key = api_key
        self.server_url = server_url.rstrip("/")
        self.agent_name = agent_name

        self._game_id: Optional[str] = None
        self._room_id: Optional[str] = None
        self._seat: Optional[int] = None
        self._role: Optional[str] = None
        self._game_state: Optional[GameState] = None
        self._connected = False
        self._running = False

        self._rest = ArenaRESTClient(server_url, api_key)
        self._sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=10,
            reconnection_delay=2,
            reconnection_delay_max=30,
            logger=False,
        )
        self._register_handlers()

    # -- properties --

    @property
    def game_id(self) -> Optional[str]:
        return self._game_id

    @property
    def room_id(self) -> Optional[str]:
        return self._room_id

    @property
    def seat(self) -> Optional[int]:
        return self._seat

    @property
    def role(self) -> Optional[str]:
        return self._role

    @property
    def game_state(self) -> Optional[GameState]:
        return self._game_state

    @property
    def rest(self) -> ArenaRESTClient:
        return self._rest

    @property
    def is_connected(self) -> bool:
        return self._connected

    # -- lifecycle --

    async def connect(self, server_url: Optional[str] = None, api_key: Optional[str] = None) -> None:
        url = (server_url or self.server_url).rstrip("/")
        key = api_key or self.api_key

        if not self._game_id:
            raise ArenaConnectionError("No game_id set. Call join_room() first or set_game_id().")

        auth = {"api_key": key, "game_id": self._game_id}
        try:
            await self._sio.connect(
                f"{url}/ws",
                namespaces=["/agent"],
                auth=auth,
                wait_timeout=15,
            )
            self._connected = True
            logger.info("%s connected to %s (game %s)", self.agent_name, url, self._game_id)
        except Exception as exc:
            raise ArenaConnectionError(f"Failed to connect to {url}: {exc}") from exc

    async def disconnect(self) -> None:
        if self._sio.connected:
            await self._sio.disconnect()
        self._connected = False

    async def join_room(self, room_id: str) -> Dict[str, Any]:
        self._room_id = room_id
        result = await self._rest.join_room(room_id)
        self._seat = result.get("seat")
        logger.info("%s joined room %s at seat %s", self.agent_name, room_id, self._seat)
        return result

    async def leave_room(self) -> Dict[str, Any]:
        if not self._room_id:
            return {"message": "Not in a room"}
        result = await self._rest.leave_room(self._room_id)
        self._room_id = None
        self._seat = None
        return result

    def set_game_id(self, game_id: str) -> None:
        self._game_id = game_id

    async def submit_action(self, action: Action) -> Dict[str, Any]:
        if not self._game_id:
            raise ArenaConnectionError("No active game")
        return await self._rest.submit_action(self._game_id, action)

    async def send_speech(self, content: str) -> Dict[str, Any]:
        return await self.submit_action(Action(action_type="speech", content=content))

    async def submit_vote(self, target: Optional[int] = None) -> Dict[str, Any]:
        if target is None:
            return await self.submit_action(Action(action_type="vote_abstain"))
        return await self.submit_action(Action(action_type="vote", target=target))

    # -- main loop --

    def run(self) -> None:
        asyncio.run(self.run_async())

    async def run_async(self) -> None:
        self._running = True
        if not self._connected:
            await self.connect()
        logger.info("%s running — waiting for game events...", self.agent_name)
        try:
            await self._sio.wait()
        except asyncio.CancelledError:
            logger.info("%s run cancelled", self.agent_name)
        finally:
            self._running = False
            await self.disconnect()
            await self._rest.close()

    async def stop(self) -> None:
        self._running = False
        await self.disconnect()

    # -- callbacks (override these) --

    async def on_game_start(self, event: GameEvent) -> None:
        pass

    async def on_night_action(self, event: GameEvent) -> Optional[Action]:
        return None

    async def on_speech_turn(self, event: GameEvent) -> Optional[Action]:
        return None

    async def on_vote(self, event: GameEvent) -> Optional[Action]:
        return None

    async def on_game_end(self, event: GameEvent) -> None:
        pass

    async def on_game_sync(self, data: Dict[str, Any]) -> None:
        pass

    async def on_player_speech(self, data: Dict[str, Any]) -> None:
        pass

    async def on_player_death(self, data: Dict[str, Any]) -> None:
        pass

    async def on_vote_result(self, data: Dict[str, Any]) -> None:
        pass

    async def on_werewolf_chat(self, data: Dict[str, Any]) -> None:
        pass

    async def on_action_ack(self, data: Dict[str, Any]) -> None:
        pass

    async def on_action_rejected(self, data: Dict[str, Any]) -> None:
        logger.warning("%s action rejected: %s", self.agent_name, data.get("reason", "unknown"))

    # -- internal --

    def _register_handlers(self) -> None:
        ns = "/agent"

        @self._sio.on("connect", namespace=ns)
        async def _on_connect() -> None:
            self._connected = True

        @self._sio.on("disconnect", namespace=ns)
        async def _on_disconnect() -> None:
            self._connected = False

        @self._sio.on("game.sync", namespace=ns)
        async def _on_game_sync(data: dict) -> None:
            self._update_state_from_sync(data)
            await self.on_game_sync(data)

        @self._sio.on("game.start", namespace=ns)
        async def _on_game_start(data: dict) -> None:
            self._role = data.get("your_role")
            self._seat = data.get("your_seat")
            event = self._make_event("game.start", data)
            await self.on_game_start(event)

        @self._sio.on("phase.night", namespace=ns)
        async def _on_phase_night(data: dict) -> None:
            event = self._make_event("phase.night", data)
            action = await self.on_night_action(event)
            if action is not None:
                await self._submit_action_safe(action)

        @self._sio.on("phase.day.speech", namespace=ns)
        async def _on_phase_speech(data: dict) -> None:
            if data.get("is_your_turn", False):
                event = self._make_event("phase.day.speech", data)
                action = await self.on_speech_turn(event)
                if action is not None:
                    await self._submit_action_safe(action)

        @self._sio.on("phase.day.vote", namespace=ns)
        async def _on_phase_vote(data: dict) -> None:
            event = self._make_event("phase.day.vote", data)
            action = await self.on_vote(event)
            if action is not None:
                await self._submit_action_safe(action)

        @self._sio.on("game.end", namespace=ns)
        async def _on_game_end(data: dict) -> None:
            event = self._make_event("game.end", data)
            await self.on_game_end(event)
            await self.stop()

        @self._sio.on("player.speech", namespace=ns)
        async def _on_player_speech(data: dict) -> None:
            await self.on_player_speech(data)

        @self._sio.on("player.death", namespace=ns)
        async def _on_player_death(data: dict) -> None:
            await self.on_player_death(data)

        @self._sio.on("vote.result", namespace=ns)
        async def _on_vote_result(data: dict) -> None:
            await self.on_vote_result(data)

        @self._sio.on("werewolf.chat", namespace=ns)
        async def _on_werewolf_chat(data: dict) -> None:
            await self.on_werewolf_chat(data)

        @self._sio.on("action.ack", namespace=ns)
        async def _on_action_ack(data: dict) -> None:
            await self.on_action_ack(data)

        @self._sio.on("action.rejected", namespace=ns)
        async def _on_action_rejected(data: dict) -> None:
            await self.on_action_rejected(data)

    def _make_event(self, event_type: str, data: dict) -> GameEvent:
        return GameEvent(event_type=event_type, game_id=self._game_id or "", data=data)

    def _update_state_from_sync(self, data: dict) -> None:
        self._game_id = data.get("game_id", self._game_id)
        self._role = data.get("your_role", self._role)
        self._seat = data.get("your_seat", self._seat)
        self._game_state = GameState(
            game_id=data.get("game_id", ""),
            status=data.get("status", ""),
            current_phase=data.get("current_phase"),
            current_round=data.get("current_round", 0),
            my_seat=data.get("your_seat"),
            my_role=data.get("your_role"),
            players=[],
        )

    async def _submit_action_safe(self, action: Action) -> None:
        try:
            result = await self.submit_action(action)
            if not result.get("success", True):
                logger.warning("%s action failed: %s", self.agent_name, result.get("message", "unknown"))
        except Exception as exc:
            logger.error("%s failed to submit action: %s", self.agent_name, exc)
