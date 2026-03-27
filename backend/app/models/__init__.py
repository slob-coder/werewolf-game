"""Database models package — import all models so Alembic can detect them."""

from app.models.access_key import AccessKey  # noqa: F401
from app.models.action import GameAction  # noqa: F401
from app.models.agent import Agent  # noqa: F401
from app.models.agent_report import AgentReport  # noqa: F401
from app.models.event import GameEvent  # noqa: F401
from app.models.game import Game  # noqa: F401
from app.models.player import GamePlayer  # noqa: F401
from app.models.room import Room  # noqa: F401
from app.models.server_exception import ServerException  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "User",
    "Agent",
    "AgentReport",
    "AccessKey",
    "Room",
    "Game",
    "GamePlayer",
    "GameEvent",
    "GameAction",
    "ServerException",
]
