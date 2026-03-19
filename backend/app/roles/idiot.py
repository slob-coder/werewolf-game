"""Idiot role — survives first vote execution but loses voting rights."""

from __future__ import annotations

from typing import Any

from app.engine.state_machine import GamePhase
from app.roles.base import ActionType, Faction, RoleBase
from app.roles.registry import RoleRegistry


@RoleRegistry.register
class Idiot(RoleBase):
    name = "idiot"
    display_name = "白痴"
    faction = Faction.GOD
    has_night_action = False
    action_phase = None
    priority = 100

    def __init__(self) -> None:
        self.has_revealed: bool = False  # True after surviving a vote
        self.can_vote: bool = True

    def get_action_types(self) -> list[ActionType]:
        return []  # No special action

    def can_act(self, phase: GamePhase, *, is_alive: bool = True, **kwargs: Any) -> bool:
        return False  # Idiot has no active ability

    def on_vote_execution(self) -> bool:
        """Called when idiot is voted out.

        Returns True if the idiot survives (first time only).
        After surviving, the idiot loses voting rights.
        """
        if not self.has_revealed:
            self.has_revealed = True
            self.can_vote = False
            return True  # survives
        return False  # dies
