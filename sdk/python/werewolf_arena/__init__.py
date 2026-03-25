"""Werewolf Arena — Python Agent SDK."""

from werewolf_arena.agent import WerewolfAgent
from werewolf_arena.client import ArenaRESTClient
from werewolf_arena.exceptions import (
    ArenaAPIError,
    ArenaConnectionError,
    ArenaError,
    ArenaTimeoutError,
)
from werewolf_arena.models import (
    Action,
    GameEvent,
    GamePhase,
    GameState,
    PhaseInfo,
    PlayerInfo,
    RoleConfig,
    RoomInfo,
    RoomStatus,
)

__all__ = [
    "WerewolfAgent",
    "ArenaRESTClient",
    "Action",
    "GameEvent",
    "GameState",
    "GamePhase",
    "PhaseInfo",
    "PlayerInfo",
    "RoleConfig",
    "RoomInfo",
    "RoomStatus",
    "ArenaError",
    "ArenaAPIError",
    "ArenaConnectionError",
    "ArenaTimeoutError",
]

__version__ = "0.1.0"
