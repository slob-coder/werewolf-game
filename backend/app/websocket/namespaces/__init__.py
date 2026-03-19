"""Socket.IO namespace package."""

from app.websocket.namespaces.agent_ns import AgentNamespace
from app.websocket.namespaces.lobby_ns import LobbyNamespace
from app.websocket.namespaces.spectator_ns import SpectatorNamespace

__all__ = ["AgentNamespace", "SpectatorNamespace", "LobbyNamespace"]
