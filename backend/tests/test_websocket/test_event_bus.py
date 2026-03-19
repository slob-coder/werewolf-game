"""Tests for the Redis EventBus."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.websocket.event_bus import EventBus


@pytest.fixture
def event_bus_instance():
    """Create a fresh EventBus instance for each test."""
    return EventBus()


class TestEventBusPublish:
    """Tests for event publishing."""

    @pytest.mark.asyncio
    async def test_publish_game_event(self, event_bus_instance: EventBus):
        """Publishing a game event should call Redis.publish with correct channel."""
        mock_redis = AsyncMock()
        mock_redis.pubsub.return_value = AsyncMock()
        event_bus_instance._redis = mock_redis

        await event_bus_instance.publish_game_event(
            game_id="game-123",
            event_type="phase.change",
            data={"phase": "night_werewolf"},
            phase="night_werewolf",
            round_number=1,
        )

        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        channel = call_args[0][0]
        payload = json.loads(call_args[0][1])

        assert channel == "game:game-123:events"
        assert payload["event_type"] == "phase.change"
        assert payload["game_id"] == "game-123"
        assert payload["phase"] == "night_werewolf"
        assert payload["round"] == 1
        assert "timestamp" in payload

    @pytest.mark.asyncio
    async def test_publish_lobby_event(self, event_bus_instance: EventBus):
        """Publishing a lobby event should use the lobby channel."""
        mock_redis = AsyncMock()
        event_bus_instance._redis = mock_redis

        await event_bus_instance.publish_lobby_event(
            event_type="room.created",
            data={"room_id": "room-1", "name": "Test Room"},
        )

        mock_redis.publish.assert_called_once()
        channel = mock_redis.publish.call_args[0][0]
        assert channel == "lobby:events"

    @pytest.mark.asyncio
    async def test_publish_without_start(self, event_bus_instance: EventBus):
        """Publishing without starting the bus should not crash."""
        # _redis is None
        await event_bus_instance.publish_game_event(
            game_id="game-1",
            event_type="test",
            data={},
        )
        # Should not raise


class TestEventBusSubscribe:
    """Tests for event subscription and handler dispatch."""

    @pytest.mark.asyncio
    async def test_subscribe_game(self, event_bus_instance: EventBus):
        """Subscribing to a game channel should register the handler."""
        mock_pubsub = AsyncMock()
        event_bus_instance._pubsub = mock_pubsub

        handler = AsyncMock()
        await event_bus_instance.subscribe_game("game-1", handler)

        expected_channel = "game:game-1:events"
        assert expected_channel in event_bus_instance._handlers
        assert handler in event_bus_instance._handlers[expected_channel]
        mock_pubsub.subscribe.assert_called_once_with(expected_channel)

    @pytest.mark.asyncio
    async def test_unsubscribe_game(self, event_bus_instance: EventBus):
        """Unsubscribing should remove handlers and call pubsub.unsubscribe."""
        mock_pubsub = AsyncMock()
        event_bus_instance._pubsub = mock_pubsub

        handler = AsyncMock()
        await event_bus_instance.subscribe_game("game-1", handler)
        await event_bus_instance.unsubscribe_game("game-1")

        expected_channel = "game:game-1:events"
        assert expected_channel not in event_bus_instance._handlers
        mock_pubsub.unsubscribe.assert_called_once_with(expected_channel)

    @pytest.mark.asyncio
    async def test_subscribe_lobby(self, event_bus_instance: EventBus):
        """Subscribing to the lobby channel should register the handler."""
        mock_pubsub = AsyncMock()
        event_bus_instance._pubsub = mock_pubsub

        handler = AsyncMock()
        await event_bus_instance.subscribe_lobby(handler)

        assert "lobby:events" in event_bus_instance._handlers
        mock_pubsub.subscribe.assert_called_once_with("lobby:events")


class TestEventBusLifecycle:
    """Tests for start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_stop_clears_handlers(self, event_bus_instance: EventBus):
        """Stopping the bus should clear all handlers."""
        mock_pubsub = AsyncMock()
        mock_pubsub.get_message = AsyncMock(return_value=None)

        mock_redis = AsyncMock()
        # pubsub() is a sync method that returns a PubSub object
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        await event_bus_instance.start(mock_redis)

        handler = AsyncMock()
        await event_bus_instance.subscribe_game("game-1", handler)

        await event_bus_instance.stop()

        assert len(event_bus_instance._handlers) == 0
        assert event_bus_instance._running is False
