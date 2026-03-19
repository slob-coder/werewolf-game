"""Villager role — ordinary townsperson with no special ability."""

from __future__ import annotations

from typing import Any

from app.engine.state_machine import GamePhase
from app.roles.base import ActionType, Faction, RoleBase
from app.roles.registry import RoleRegistry


@RoleRegistry.register
class Villager(RoleBase):
    name = "villager"
    display_name = "村民"
    faction = Faction.VILLAGER
    has_night_action = False
    action_phase = None
    priority = 100

    def get_action_types(self) -> list[ActionType]:
        return []

    def can_act(self, phase: GamePhase, *, is_alive: bool = True, **kwargs: Any) -> bool:
        return False
