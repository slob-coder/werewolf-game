"""Tests for the ReconnectionManager."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.websocket.reconnection import ReconnectionManager


@pytest.fixture
def manager():
    """Create a fresh ReconnectionManager for each test."""
    return ReconnectionManager(timeout_seconds=2)


class TestDisconnect:
    """Tests for disconnect handling."""

    @pytest.mark.asyncio
    async def test_on_disconnect_creates_session(self, manager: ReconnectionManager):
        """Disconnecting should create a DisconnectedSession."""
        await manager.on_disconnect("agent-1", "game-1", "player-1", "sid-1")

        assert manager.is_disconnected("agent-1", "game-1")
        assert manager.disconnected_count == 1

    @pytest.mark.asyncio
    async def test_on_disconnect_replaces_existing(self, manager: ReconnectionManager):
        """Disconnecting again should replace existing session."""
        await manager.on_disconnect("agent-1", "game-1", "player-1", "sid-1")
        await manager.on_disconnect("agent-1", "game-1", "player-1", "sid-2")

        assert manager.disconnected_count == 1
        session = manager.get_session("agent-1", "game-1")
        assert session is not None
        assert session.sid == "sid-2"


class TestReconnect:
    """Tests for reconnect handling."""

    @pytest.mark.asyncio
    async def test_on_reconnect_returns_session(self, manager: ReconnectionManager):
        """Reconnecting should return the session with buffered events."""
        await manager.on_disconnect("agent-1", "game-1", "player-1", "sid-1")

        manager.buffer_event("agent-1", "game-1", {"event": "phase.change"})
        manager.buffer_event("agent-1", "game-1", {"event": "game.end"})

        session = await manager.on_reconnect("agent-1", "game-1")

        assert session is not None
        assert len(session.pending_events) == 2
        assert not manager.is_disconnected("agent-1", "game-1")

    @pytest.mark.asyncio
    async def test_on_reconnect_no_session(self, manager: ReconnectionManager):
        """Reconnecting without a disconnect should return None."""
        session = await manager.on_reconnect("agent-1", "game-1")
        assert session is None


class TestBufferEvents:
    """Tests for event buffering."""

    @pytest.mark.asyncio
    async def test_buffer_event_success(self, manager: ReconnectionManager):
        """Buffering an event should succeed for disconnected agents."""
        await manager.on_disconnect("agent-1", "game-1", "player-1", "sid-1")

        result = manager.buffer_event(
            "agent-1", "game-1", {"event": "test"}
        )
        assert result is True

        session = manager.get_session("agent-1", "game-1")
        assert session is not None
        assert len(session.pending_events) == 1

    def test_buffer_event_no_session(self, manager: ReconnectionManager):
        """Buffering for a non-disconnected agent should return False."""
        result = manager.buffer_event("agent-x", "game-1", {"event": "test"})
        assert result is False


class TestTimeout:
    """Tests for reconnect timeout."""

    @pytest.mark.asyncio
    async def test_timeout_fires_callback(self, manager: ReconnectionManager):
        """Timeout should fire the callback and remove the session."""
        callback = AsyncMock()
        manager.set_timeout_callback(callback)

        # Use very short timeout
        manager._timeout_seconds = 0.1
        await manager.on_disconnect("agent-1", "game-1", "player-1", "sid-1")

        # Wait for timeout
        await asyncio.sleep(0.3)

        callback.assert_called_once_with("agent-1", "game-1")
        assert not manager.is_disconnected("agent-1", "game-1")

    @pytest.mark.asyncio
    async def test_reconnect_cancels_timeout(self, manager: ReconnectionManager):
        """Reconnecting before timeout should cancel the callback."""
        callback = AsyncMock()
        manager.set_timeout_callback(callback)

        manager._timeout_seconds = 1
        await manager.on_disconnect("agent-1", "game-1", "player-1", "sid-1")

        # Reconnect immediately
        await manager.on_reconnect("agent-1", "game-1")

        # Wait to make sure callback doesn't fire
        await asyncio.sleep(0.2)

        callback.assert_not_called()


class TestCleanup:
    """Tests for game cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_game(self, manager: ReconnectionManager):
        """Cleanup should remove all sessions for a game."""
        await manager.on_disconnect("agent-1", "game-1", "player-1", "sid-1")
        await manager.on_disconnect("agent-2", "game-1", "player-2", "sid-2")
        await manager.on_disconnect("agent-3", "game-2", "player-3", "sid-3")

        removed = manager.cleanup_game("game-1")
        assert removed == 2
        assert manager.disconnected_count == 1
        assert manager.is_disconnected("agent-3", "game-2")
