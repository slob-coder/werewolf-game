"""REST client for the Werewolf Arena backend API."""

from __future__ import annotations

import logging
from typing import Any, Optional, List, Dict

import httpx

from werewolf_arena.exceptions import ArenaAPIError, ArenaConnectionError
from werewolf_arena.models import (
    Action, GameEvent, GameState, PlayerInfo, RoomInfo, SlotInfo,
)

logger = logging.getLogger(__name__)


class ArenaRESTClient:
    """Async HTTP client for the Arena /api/v1 endpoints."""

    def __init__(self, server_url: str, api_key: str, *, timeout: float = 30.0) -> None:
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self._base_url = f"{self.server_url}/api/v1"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-Agent-Key": self.api_key},
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            resp = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise ArenaConnectionError(f"HTTP request failed: {exc}") from exc
        if resp.status_code >= 400:
            detail = resp.text
            try:
                body = resp.json()
                detail = body.get("detail", detail)
            except Exception:
                pass
            raise ArenaAPIError(resp.status_code, detail)
        if resp.status_code == 204:
            return {}
        return resp.json()

    async def list_rooms(self, status: Optional[str] = None) -> List[RoomInfo]:
        params: Dict[str, str] = {}
        if status:
            params["status"] = status
        data = await self._request("GET", "/rooms", params=params)
        return [RoomInfo(**r) for r in data]

    async def get_room(self, room_id: str) -> RoomInfo:
        data = await self._request("GET", f"/rooms/{room_id}")
        return RoomInfo(**data)

    async def join_room(self, room_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/rooms/{room_id}/join")

    async def leave_room(self, room_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/rooms/{room_id}/leave")

    async def toggle_ready(self, room_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/rooms/{room_id}/ready")

    async def get_game_state(self, game_id: str) -> GameState:
        data = await self._request("GET", f"/games/{game_id}/state")
        return GameState(**data)

    async def submit_action(self, game_id: str, action: Action) -> Dict[str, Any]:
        return await self._request("POST", f"/games/{game_id}/action", json=action.to_request_body())

    async def get_game_events(self, game_id: str) -> List[GameEvent]:
        data = await self._request("GET", f"/games/{game_id}/events")
        events = data.get("events", [])
        return [GameEvent(**e) for e in events]

    async def get_role_presets(self) -> List[Dict[str, Any]]:
        data = await self._request("GET", "/roles/presets")
        return data.get("presets", [])

    async def get_available_roles(self) -> List[Dict[str, Any]]:
        data = await self._request("GET", "/roles/available")
        return data.get("roles", [])

    async def get_game_stats(self, game_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/games/{game_id}/stats")

    async def get_game_replay(self, game_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/games/{game_id}/replay")

    async def health(self) -> Dict[str, str]:
        return await self._request("GET", "/health")
