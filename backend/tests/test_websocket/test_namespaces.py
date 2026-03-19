"""Tests for Socket.IO namespace authentication and event handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.websocket.namespaces.agent_ns import AgentNamespace
from app.websocket.namespaces.lobby_ns import LobbyNamespace
from app.websocket.namespaces.spectator_ns import SpectatorNamespace


def _make_mock_sio():
    """Create a mock Socket.IO server."""
    sio = AsyncMock()
    sio.save_session = AsyncMock()
    sio.get_session = AsyncMock(return_value={})
    sio.enter_room = MagicMock()
    sio.emit = AsyncMock()
    return sio


class TestAgentNamespaceAuth:
    """Tests for agent namespace connection authentication."""

    @pytest.mark.asyncio
    async def test_connect_no_auth(self):
        """Agent connect without auth should be rejected."""
        sio = _make_mock_sio()
        ns = AgentNamespace(sio)
        result = await ns.on_connect("sid-1", {}, auth=None)
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_missing_api_key(self):
        """Agent connect without api_key should be rejected."""
        sio = _make_mock_sio()
        ns = AgentNamespace(sio)
        result = await ns.on_connect("sid-1", {}, auth={"game_id": "g-1"})
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_missing_game_id(self):
        """Agent connect without game_id should be rejected."""
        sio = _make_mock_sio()
        ns = AgentNamespace(sio)
        result = await ns.on_connect("sid-1", {}, auth={"api_key": "k-1"})
        assert result is False


class TestSpectatorNamespaceAuth:
    """Tests for spectator namespace connection authentication."""

    @pytest.mark.asyncio
    async def test_connect_no_auth(self):
        """Spectator connect without auth should be rejected."""
        sio = _make_mock_sio()
        ns = SpectatorNamespace(sio)
        result = await ns.on_connect("sid-1", {}, auth=None)
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_missing_token(self):
        """Spectator connect without token should be rejected."""
        sio = _make_mock_sio()
        ns = SpectatorNamespace(sio)
        result = await ns.on_connect("sid-1", {}, auth={"game_id": "g-1"})
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_missing_game_id(self):
        """Spectator connect without game_id should be rejected."""
        sio = _make_mock_sio()
        ns = SpectatorNamespace(sio)
        result = await ns.on_connect("sid-1", {}, auth={"token": "t-1"})
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_invalid_jwt(self):
        """Spectator connect with invalid JWT should be rejected."""
        sio = _make_mock_sio()
        ns = SpectatorNamespace(sio)
        result = await ns.on_connect(
            "sid-1", {}, auth={"token": "invalid-jwt", "game_id": "g-1"}
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_valid_jwt(self):
        """Spectator connect with valid JWT should be accepted."""
        from app.security.auth import create_access_token

        sio = _make_mock_sio()
        ns = SpectatorNamespace(sio)

        token = create_access_token({"sub": "user-123"})

        # Mock the DB call to build god view
        with patch.object(ns, "_build_god_view", new_callable=AsyncMock) as mock_build:
            mock_build.return_value = {"game_id": "g-1", "players": []}
            result = await ns.on_connect(
                "sid-1", {}, auth={"token": token, "game_id": "g-1"}
            )

        assert result is True
        sio.save_session.assert_called_once()
        sio.enter_room.assert_called_once()


class TestLobbyNamespaceAuth:
    """Tests for lobby namespace (no auth required)."""

    @pytest.mark.asyncio
    async def test_connect_no_auth(self):
        """Lobby connect should always succeed, no auth needed."""
        sio = _make_mock_sio()
        ns = LobbyNamespace(sio)
        result = await ns.on_connect("sid-1", {}, auth=None)
        assert result is True
        sio.enter_room.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_auth(self):
        """Lobby connect with auth should still succeed."""
        sio = _make_mock_sio()
        ns = LobbyNamespace(sio)
        result = await ns.on_connect("sid-1", {}, auth={"some": "data"})
        assert result is True


class TestAgentNamespaceEvents:
    """Tests for agent namespace event handling."""

    @pytest.mark.asyncio
    async def test_push_to_game(self):
        """push_to_game should emit to the correct game room."""
        sio = _make_mock_sio()
        ns = AgentNamespace(sio)

        await ns.push_to_game("game-1", "phase.change", {"phase": "night"})

        sio.emit.assert_called_once_with(
            "phase.change",
            {"phase": "night"},
            room="game:game-1",
            namespace="/agent",
        )

    @pytest.mark.asyncio
    async def test_push_to_agent(self):
        """push_to_agent should emit to a specific SID."""
        sio = _make_mock_sio()
        ns = AgentNamespace(sio)

        await ns.push_to_agent("sid-1", "action.ack", {"status": "ok"})

        sio.emit.assert_called_once_with(
            "action.ack",
            {"status": "ok"},
            room="sid-1",
            namespace="/agent",
        )

    @pytest.mark.asyncio
    async def test_heartbeat(self):
        """Heartbeat should respond with ack."""
        sio = _make_mock_sio()
        ns = AgentNamespace(sio)

        await ns.on_heartbeat("sid-1")

        sio.emit.assert_called_once_with(
            "heartbeat.ack",
            {"status": "ok"},
            room="sid-1",
            namespace="/agent",
        )

    @pytest.mark.asyncio
    async def test_action_without_session(self):
        """Action submission without session should be rejected."""
        sio = _make_mock_sio()
        sio.get_session = AsyncMock(return_value=None)
        ns = AgentNamespace(sio)

        await ns.on_agent_action("sid-1", {"action_type": "vote", "target_seat": 2})

        # Should emit rejection
        sio.emit.assert_called_once()
        call = sio.emit.call_args
        assert call[0][0] == "action.rejected"


class TestSpectatorNamespaceEvents:
    """Tests for spectator namespace event pushing."""

    @pytest.mark.asyncio
    async def test_push_to_spectators(self):
        """push_to_game_spectators should emit to the spectator room."""
        sio = _make_mock_sio()
        ns = SpectatorNamespace(sio)

        await ns.push_to_game_spectators(
            "game-1", "phase.change", {"phase": "night"}
        )

        sio.emit.assert_called_once_with(
            "phase.change",
            {"phase": "night"},
            room="spectator:game-1",
            namespace="/spectator",
        )


class TestLobbyNamespaceEvents:
    """Tests for lobby namespace event pushing."""

    @pytest.mark.asyncio
    async def test_push_room_update(self):
        """push_room_update should emit to the lobby room."""
        sio = _make_mock_sio()
        ns = LobbyNamespace(sio)

        await ns.push_room_update(
            "room.created",
            {"room_id": "room-1", "name": "Test Room"},
        )

        sio.emit.assert_called_once_with(
            "room.created",
            {"room_id": "room-1", "name": "Test Room"},
            room="lobby",
            namespace="/lobby",
        )
