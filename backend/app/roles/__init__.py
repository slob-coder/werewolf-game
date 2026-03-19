"""Roles package — importing this module triggers auto-registration."""

from app.roles.base import ActionType, Faction, GameAction, ActionEffect, RoleBase  # noqa: F401
from app.roles.registry import RoleRegistry  # noqa: F401

# Import each role so the @RoleRegistry.register decorator fires.
from app.roles.werewolf import Werewolf  # noqa: F401
from app.roles.seer import Seer  # noqa: F401
from app.roles.witch import Witch  # noqa: F401
from app.roles.hunter import Hunter  # noqa: F401
from app.roles.guard import Guard  # noqa: F401
from app.roles.idiot import Idiot  # noqa: F401
from app.roles.villager import Villager  # noqa: F401

__all__ = [
    "ActionType",
    "Faction",
    "GameAction",
    "ActionEffect",
    "RoleBase",
    "RoleRegistry",
    "Werewolf",
    "Seer",
    "Witch",
    "Hunter",
    "Guard",
    "Idiot",
    "Villager",
]
