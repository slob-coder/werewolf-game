"""Seer role — checks one player's identity each night."""

from __future__ import annotations

from typing import Any

from app.engine.state_machine import GamePhase
from app.roles.base import ActionType, Faction, RoleBase
from app.roles.registry import RoleRegistry


@RoleRegistry.register
class Seer(RoleBase):
    name = "seer"
    display_name = "预言家"
    faction = Faction.GOD
    has_night_action = True
    action_phase = GamePhase.NIGHT_SEER
    priority = 20

    def get_action_types(self) -> list[ActionType]:
        return [ActionType.SEER_CHECK]

    def can_act(self, phase: GamePhase, *, is_alive: bool = True, **kwargs: Any) -> bool:
        return is_alive and phase == GamePhase.NIGHT_SEER
