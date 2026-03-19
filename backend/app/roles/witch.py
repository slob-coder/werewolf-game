"""Witch role — one save potion and one poison potion, each usable once."""

from __future__ import annotations

from typing import Any

from app.engine.state_machine import GamePhase
from app.roles.base import ActionType, Faction, RoleBase
from app.roles.registry import RoleRegistry


@RoleRegistry.register
class Witch(RoleBase):
    name = "witch"
    display_name = "女巫"
    faction = Faction.GOD
    has_night_action = True
    action_phase = GamePhase.NIGHT_WITCH
    priority = 30

    def __init__(self) -> None:
        self.has_save_potion: bool = True
        self.has_poison_potion: bool = True

    def get_action_types(self) -> list[ActionType]:
        types: list[ActionType] = []
        if self.has_save_potion:
            types.append(ActionType.WITCH_SAVE)
        if self.has_poison_potion:
            types.append(ActionType.WITCH_POISON)
        types.append(ActionType.WITCH_SKIP)
        return types

    def can_act(self, phase: GamePhase, *, is_alive: bool = True, **kwargs: Any) -> bool:
        return is_alive and phase == GamePhase.NIGHT_WITCH

    def use_save(self) -> bool:
        if self.has_save_potion:
            self.has_save_potion = False
            return True
        return False

    def use_poison(self) -> bool:
        if self.has_poison_potion:
            self.has_poison_potion = False
            return True
        return False
