"""Werewolf role — the core evil faction role."""

from __future__ import annotations

from typing import Any

from app.engine.state_machine import GamePhase
from app.roles.base import ActionType, Faction, RoleBase
from app.roles.registry import RoleRegistry


@RoleRegistry.register
class Werewolf(RoleBase):
    name = "werewolf"
    display_name = "狼人"
    faction = Faction.WEREWOLF
    has_night_action = True
    action_phase = GamePhase.NIGHT_WEREWOLF
    priority = 10

    def get_action_types(self) -> list[ActionType]:
        return [ActionType.WEREWOLF_KILL, ActionType.WEREWOLF_CHAT]

    def can_act(self, phase: GamePhase, *, is_alive: bool = True, **kwargs: Any) -> bool:
        return is_alive and phase == GamePhase.NIGHT_WEREWOLF
