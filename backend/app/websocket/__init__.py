"""WebSocket package — Socket.IO server, event bus, and reconnection manager."""

from app.websocket.event_bus import EventBus, event_bus
from app.websocket.reconnection import ReconnectionManager, reconnection_manager
from app.websocket.server import agent_namespace, lobby_namespace, sio, socket_app, spectator_namespace

__all__ = [
    "sio",
    "socket_app",
    "agent_namespace",
    "spectator_namespace",
    "lobby_namespace",
    "event_bus",
    "EventBus",
    "reconnection_manager",
    "ReconnectionManager",
]
