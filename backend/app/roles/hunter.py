"""Hunter role — can shoot one player on death (except when poisoned)."""

from __future__ import annotations

from typing import Any

from app.engine.state_machine import GamePhase
from app.roles.base import ActionType, Faction, RoleBase
from app.roles.registry import RoleRegistry


@RoleRegistry.register
class Hunter(RoleBase):
    name = "hunter"
    display_name = "猎人"
    faction = Faction.GOD
    has_night_action = False
    action_phase = None
    priority = 100  # passive — resolved reactively

    def get_action_types(self) -> list[ActionType]:
        return [ActionType.HUNTER_SHOOT, ActionType.HUNTER_SKIP]

    def can_act(self, phase: GamePhase, *, is_alive: bool = True, **kwargs: Any) -> bool:
        # Hunter can act in the dedicated hunter phases
        return phase in (GamePhase.HUNTER_SHOOT, GamePhase.NIGHT_HUNTER)

    def on_death(self, cause: str, **kwargs: Any) -> dict[str, Any] | None:
        """Hunter can shoot on death *unless* poisoned by the witch."""
        if cause == "poison":
            return {"hunter_can_shoot": False}
        return {"hunter_can_shoot": True}
