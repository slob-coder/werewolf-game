"""Socket.IO server setup and FastAPI integration.

Creates the ``python-socketio`` AsyncServer, registers all namespaces,
and provides the ASGI app to mount on FastAPI.
"""

from __future__ import annotations

import logging

import socketio

from app.websocket.namespaces.agent_ns import AgentNamespace
from app.websocket.namespaces.lobby_ns import LobbyNamespace
from app.websocket.namespaces.spectator_ns import SpectatorNamespace

logger = logging.getLogger(__name__)

# Create the Socket.IO async server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",  # CORS handled by FastAPI middleware
    logger=False,
    engineio_logger=False,
)

# Create namespace instances
agent_namespace = AgentNamespace(sio)
spectator_namespace = SpectatorNamespace(sio)
lobby_namespace = LobbyNamespace(sio)

# Register namespaces
sio.register_namespace(agent_namespace)
sio.register_namespace(spectator_namespace)
sio.register_namespace(lobby_namespace)

# ASGI app to mount on FastAPI
#socket_app = socketio.ASGIApp(sio)
socket_app = socketio.ASGIApp(sio, socketio_path="ws/socket.io")

def get_sio() -> socketio.AsyncServer:
    """Return the Socket.IO server instance."""
    return sio
