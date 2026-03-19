"""Night resolver — collects all night actions and computes deaths."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.roles.base import ActionType

logger = logging.getLogger(__name__)


@dataclass
class NightAction:
    """A single night action recorded by the engine."""

    actor_seat: int
    role: str
    action_type: ActionType
    target_seat: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class NightResult:
    """Outcome of a single night resolution cycle."""

    killed: list[int] = field(default_factory=list)  # seats that died
    saved: list[int] = field(default_factory=list)    # seats that were saved
    protected: list[int] = field(default_factory=list)  # seats guarded
    poisoned: list[int] = field(default_factory=list)  # seats poisoned by witch
    seer_results: dict[int, str] = field(default_factory=dict)  # seat → faction
    details: list[str] = field(default_factory=list)   # human-readable log


class NightResolver:
    """Resolves all night-time actions using delayed settlement.

    Resolution priority (lower number = resolved first):
        1. Guard protect  (priority 5)
        2. Werewolf kill   (priority 10)
        3. Seer check      (priority 20)
        4. Witch save/poison (priority 30)

    Rules:
    - If guard protects the werewolf target → target survives
    - If witch saves the werewolf target → target survives
    - If *both* guard and witch save the same target → configurable
      (default: target survives — "同守同救均活")
    - Witch poison is independent of other actions
    """

    def __init__(self, *, same_guard_save_dies: bool = False):
        self._same_guard_save_dies = same_guard_save_dies

    def resolve(
        self,
        actions: list[NightAction],
        alive_seats: set[int],
        seat_to_role: dict[int, str],
    ) -> NightResult:
        """Process all night actions and produce the result.

        Args:
            actions: all submitted night actions this round
            alive_seats: set of seat numbers currently alive
            seat_to_role: mapping of seat → role name for faction lookup
        """
        result = NightResult()

        # Classify actions by type
        guard_target: int | None = None
        werewolf_target: int | None = None
        seer_target: int | None = None
        witch_save: bool = False
        witch_poison_target: int | None = None

        for a in actions:
            if a.action_type == ActionType.GUARD_PROTECT and a.target_seat is not None:
                guard_target = a.target_seat
            elif a.action_type == ActionType.WEREWOLF_KILL and a.target_seat is not None:
                werewolf_target = a.target_seat
            elif a.action_type == ActionType.SEER_CHECK and a.target_seat is not None:
                seer_target = a.target_seat
            elif a.action_type == ActionType.WITCH_SAVE:
                witch_save = True
            elif a.action_type == ActionType.WITCH_POISON and a.target_seat is not None:
                witch_poison_target = a.target_seat
            # WITCH_SKIP and other actions are no-ops for resolution

        # 1. Guard protection
        if guard_target is not None:
            result.protected.append(guard_target)
            result.details.append(f"守卫守护了 {guard_target} 号位")

        # 2. Werewolf kill resolution
        if werewolf_target is not None:
            guarded = guard_target == werewolf_target
            saved = witch_save

            if guarded and saved:
                # Both guard and witch protected — configurable
                if self._same_guard_save_dies:
                    result.killed.append(werewolf_target)
                    result.details.append(
                        f"{werewolf_target} 号位被狼人击杀，同守同救，判定死亡"
                    )
                else:
                    result.saved.append(werewolf_target)
                    result.details.append(
                        f"{werewolf_target} 号位被狼人击杀，同守同救，判定存活"
                    )
            elif guarded:
                result.saved.append(werewolf_target)
                result.details.append(
                    f"{werewolf_target} 号位被狼人击杀，但守卫守护成功"
                )
            elif saved:
                result.saved.append(werewolf_target)
                result.details.append(
                    f"{werewolf_target} 号位被狼人击杀，但女巫使用解药救活"
                )
            else:
                result.killed.append(werewolf_target)
                result.details.append(f"{werewolf_target} 号位被狼人击杀")

        # 3. Seer check
        if seer_target is not None:
            target_role = seat_to_role.get(seer_target, "unknown")
            # Return faction-level identity (werewolf vs good)
            if target_role == "werewolf":
                result.seer_results[seer_target] = "werewolf"
                result.details.append(f"预言家查验 {seer_target} 号位: 狼人")
            else:
                result.seer_results[seer_target] = "good"
                result.details.append(f"预言家查验 {seer_target} 号位: 好人")

        # 4. Witch poison (independent of kill)
        if witch_poison_target is not None:
            if witch_poison_target not in result.killed:
                result.killed.append(witch_poison_target)
            result.poisoned.append(witch_poison_target)
            result.details.append(f"{witch_poison_target} 号位被女巫毒杀")

        return result
