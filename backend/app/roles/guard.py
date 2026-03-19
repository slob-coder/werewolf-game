"""Guard role — protects one player each night (cannot repeat same target)."""

from __future__ import annotations

from typing import Any

from app.engine.state_machine import GamePhase
from app.roles.base import ActionType, Faction, RoleBase
from app.roles.registry import RoleRegistry


@RoleRegistry.register
class Guard(RoleBase):
    name = "guard"
    display_name = "守卫"
    faction = Faction.GOD
    has_night_action = True
    action_phase = GamePhase.NIGHT_WEREWOLF  # acts in the same window
    priority = 5  # resolved before werewolf kill

    def __init__(self) -> None:
        self.last_protected_seat: int | None = None

    def get_action_types(self) -> list[ActionType]:
        return [ActionType.GUARD_PROTECT]

    def can_act(self, phase: GamePhase, *, is_alive: bool = True, **kwargs: Any) -> bool:
        # Guard acts during night_werewolf phase (same timing)
        return is_alive and phase == GamePhase.NIGHT_WEREWOLF

    def protect(self, target_seat: int) -> bool:
        """Attempt to protect a seat.  Returns False if same as last night."""
        if target_seat == self.last_protected_seat:
            return False
        self.last_protected_seat = target_seat
        return True
