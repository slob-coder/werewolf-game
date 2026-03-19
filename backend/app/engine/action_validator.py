"""Action validator — checks whether a submitted action is legal."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.engine.state_machine import GamePhase
from app.roles.base import ActionType, RoleBase

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Outcome of an action validation."""

    valid: bool
    reason: str = ""


# Map action types to the phases they are allowed in
ACTION_PHASE_MAP: dict[ActionType, set[GamePhase]] = {
    ActionType.WEREWOLF_KILL: {GamePhase.NIGHT_WEREWOLF},
    ActionType.WEREWOLF_CHAT: {GamePhase.NIGHT_WEREWOLF},
    ActionType.SEER_CHECK: {GamePhase.NIGHT_SEER},
    ActionType.WITCH_SAVE: {GamePhase.NIGHT_WITCH},
    ActionType.WITCH_POISON: {GamePhase.NIGHT_WITCH},
    ActionType.WITCH_SKIP: {GamePhase.NIGHT_WITCH},
    ActionType.GUARD_PROTECT: {GamePhase.NIGHT_WEREWOLF},
    ActionType.HUNTER_SHOOT: {GamePhase.HUNTER_SHOOT, GamePhase.NIGHT_HUNTER},
    ActionType.HUNTER_SKIP: {GamePhase.HUNTER_SHOOT, GamePhase.NIGHT_HUNTER},
    ActionType.SPEECH: {GamePhase.DAY_SPEECH},
    ActionType.VOTE: {GamePhase.DAY_VOTE},
    ActionType.VOTE_ABSTAIN: {GamePhase.DAY_VOTE},
    ActionType.LAST_WORDS: {GamePhase.LAST_WORDS},
}


class ActionValidator:
    """Stateless validator for game actions."""

    def validate(
        self,
        action_type: ActionType,
        actor_seat: int,
        role: RoleBase,
        current_phase: GamePhase,
        *,
        is_alive: bool = True,
        target_seat: int | None = None,
        alive_seats: set[int] | None = None,
        already_acted: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Run all validation checks and return the result."""

        # 1. Actor must be alive (except last words / hunter on-death)
        if not is_alive and action_type not in (
            ActionType.LAST_WORDS,
            ActionType.HUNTER_SHOOT,
            ActionType.HUNTER_SKIP,
        ):
            return ValidationResult(False, "Player is dead")

        # 2. Phase check
        allowed_phases = ACTION_PHASE_MAP.get(action_type)
        if allowed_phases is None:
            return ValidationResult(False, f"Unknown action type: {action_type}")
        if current_phase not in allowed_phases:
            return ValidationResult(
                False,
                f"Action {action_type} not allowed in phase {current_phase}",
            )

        # 3. Role capability check
        role_actions = role.get_action_types()
        # Chat, speech, vote, last_words are universal (not role-specific)
        universal_actions = {
            ActionType.SPEECH,
            ActionType.VOTE,
            ActionType.VOTE_ABSTAIN,
            ActionType.LAST_WORDS,
            ActionType.WEREWOLF_CHAT,
        }
        if action_type not in universal_actions and action_type not in role_actions:
            return ValidationResult(
                False, f"Role {role.name} cannot perform {action_type}"
            )

        # 4. Duplicate action check
        if already_acted and action_type not in (
            ActionType.WEREWOLF_CHAT,
            ActionType.SPEECH,
        ):
            return ValidationResult(False, "Already acted this phase")

        # 5. Target validation (if applicable)
        needs_target = action_type in (
            ActionType.WEREWOLF_KILL,
            ActionType.SEER_CHECK,
            ActionType.WITCH_POISON,
            ActionType.GUARD_PROTECT,
            ActionType.HUNTER_SHOOT,
            ActionType.VOTE,
        )
        if needs_target:
            if target_seat is None:
                return ValidationResult(False, "Target is required")
            if alive_seats is not None and target_seat not in alive_seats:
                return ValidationResult(False, "Target is not alive")
            # Cannot target self for certain actions
            if action_type in (ActionType.WEREWOLF_KILL, ActionType.WITCH_POISON) and target_seat == actor_seat:
                return ValidationResult(False, "Cannot target self")

        # 6. Role-specific extra checks
        extra = extra or {}
        if action_type == ActionType.WITCH_SAVE:
            if not extra.get("has_save_potion", True):
                return ValidationResult(False, "Save potion already used")
        if action_type == ActionType.WITCH_POISON:
            if not extra.get("has_poison_potion", True):
                return ValidationResult(False, "Poison potion already used")
        if action_type == ActionType.GUARD_PROTECT:
            last_protected = extra.get("last_protected_seat")
            if last_protected is not None and last_protected == target_seat:
                return ValidationResult(False, "Cannot protect same target two nights in a row")

        # 7. Idiot vote restriction
        if action_type == ActionType.VOTE and not extra.get("can_vote", True):
            return ValidationResult(False, "Idiot has lost voting rights after reveal")

        return ValidationResult(True)
