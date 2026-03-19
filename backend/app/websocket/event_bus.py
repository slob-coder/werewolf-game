"""Redis Pub/Sub EventBus — cross-process event distribution.

Game events are published to channel ``game:{game_id}:events``.
Each worker subscribes to relevant channels and pushes events to
connected Socket.IO clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

EventHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


class EventBus:
    """Redis-backed publish/subscribe event bus.

    Supports per-game channels and a global ``lobby:events`` channel.
    """

    GAME_CHANNEL_PREFIX = "game:"
    GAME_CHANNEL_SUFFIX = ":events"
    LOBBY_CHANNEL = "lobby:events"

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._handlers: dict[str, list[EventHandler]] = {}
        self._listener_task: asyncio.Task[None] | None = None
        self._running = False

    # ── lifecycle ─────────────────────────────────────────────

    async def start(self, redis: aioredis.Redis) -> None:
        """Start the event bus with the given Redis connection."""
        self._redis = redis
        self._pubsub = redis.pubsub()
        self._running = True
        logger.info("EventBus started")

    async def stop(self) -> None:
        """Stop listening and clean up."""
        self._running = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        self._handlers.clear()
        logger.info("EventBus stopped")

    # ── publish ───────────────────────────────────────────────

    async def publish_game_event(
        self,
        game_id: str,
        event_type: str,
        data: dict[str, Any],
        *,
        phase: str = "",
        round_number: int = 0,
        visibility: str = "public",
    ) -> None:
        """Publish a game event to the game's Redis channel."""
        channel = f"{self.GAME_CHANNEL_PREFIX}{game_id}{self.GAME_CHANNEL_SUFFIX}"
        message = {
            "game_id": game_id,
            "event_type": event_type,
            "phase": phase,
            "round": round_number,
            "visibility": visibility,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._publish(channel, message)

    async def publish_lobby_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Publish a lobby event (room list changes, etc.)."""
        message = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._publish(self.LOBBY_CHANNEL, message)

    async def _publish(self, channel: str, message: dict[str, Any]) -> None:
        if self._redis is None:
            logger.warning("EventBus not started, dropping message on %s", channel)
            return
        payload = json.dumps(message, default=str)
        await self._redis.publish(channel, payload)
        logger.debug("Published to %s: %s", channel, message.get("event_type"))

    # ── subscribe ─────────────────────────────────────────────

    async def subscribe_game(self, game_id: str, handler: EventHandler) -> None:
        """Subscribe a handler to a game's event channel."""
        channel = f"{self.GAME_CHANNEL_PREFIX}{game_id}{self.GAME_CHANNEL_SUFFIX}"
        await self._subscribe(channel, handler)

    async def unsubscribe_game(self, game_id: str) -> None:
        """Unsubscribe from a game's event channel."""
        channel = f"{self.GAME_CHANNEL_PREFIX}{game_id}{self.GAME_CHANNEL_SUFFIX}"
        await self._unsubscribe(channel)

    async def subscribe_lobby(self, handler: EventHandler) -> None:
        """Subscribe a handler to the lobby channel."""
        await self._subscribe(self.LOBBY_CHANNEL, handler)

    async def unsubscribe_lobby(self) -> None:
        """Unsubscribe from the lobby channel."""
        await self._unsubscribe(self.LOBBY_CHANNEL)

    async def _subscribe(self, channel: str, handler: EventHandler) -> None:
        if channel not in self._handlers:
            self._handlers[channel] = []
            if self._pubsub:
                await self._pubsub.subscribe(channel)
                logger.debug("Subscribed to %s", channel)
            # Start listener on first subscription
            if self._listener_task is None and self._running:
                self._listener_task = asyncio.create_task(
                    self._listen(), name="eventbus-listener"
                )
        self._handlers[channel].append(handler)

    async def _unsubscribe(self, channel: str) -> None:
        if channel in self._handlers:
            del self._handlers[channel]
            if self._pubsub:
                await self._pubsub.unsubscribe(channel)
                logger.debug("Unsubscribed from %s", channel)

    # ── listener loop ─────────────────────────────────────────

    async def _listen(self) -> None:
        """Background task that reads messages from Redis Pub/Sub."""
        if not self._pubsub:
            return
        try:
            while self._running:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message is None:
                    await asyncio.sleep(0.01)
                    continue
                if message["type"] != "message":
                    continue

                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()

                raw_data = message["data"]
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode()

                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON on channel %s", channel)
                    continue

                handlers = self._handlers.get(channel, [])
                for handler in handlers:
                    try:
                        await handler(channel, data)
                    except Exception:
                        logger.exception(
                            "Error in handler for channel %s", channel
                        )
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("EventBus listener crashed")


# Singleton
event_bus = EventBus()
