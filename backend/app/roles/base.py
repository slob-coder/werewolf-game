"""Role base class and supporting types."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.engine.state_machine import GamePhase


class Faction(str, enum.Enum):
    WEREWOLF = "werewolf"
    VILLAGER = "villager"
    GOD = "god"


class ActionType(str, enum.Enum):
    """All possible action types an agent can submit."""

    WEREWOLF_KILL = "werewolf_kill"
    WEREWOLF_CHAT = "werewolf_chat"
    SEER_CHECK = "seer_check"
    WITCH_SAVE = "witch_save"
    WITCH_POISON = "witch_poison"
    WITCH_SKIP = "witch_skip"
    GUARD_PROTECT = "guard_protect"
    HUNTER_SHOOT = "hunter_shoot"
    HUNTER_SKIP = "hunter_skip"
    SPEECH = "speech"
    VOTE = "vote"
    VOTE_ABSTAIN = "vote_abstain"
    LAST_WORDS = "last_words"


@dataclass
class GameAction:
    """An action submitted by a player."""

    player_id: str
    action_type: ActionType
    target_seat: int | None = None
    content: str | None = None
    metadata: dict[str, Any] | None = None
    is_timeout: bool = False


@dataclass
class ActionEffect:
    """The result of executing an action inside the engine."""

    action_type: ActionType
    actor_seat: int
    target_seat: int | None = None
    success: bool = True
    data: dict[str, Any] = field(default_factory=dict)


class RoleBase(ABC):
    """Abstract base class for all roles.

    Sub-classes must set the class-level attributes and implement the
    abstract helpers.
    """

    name: str = ""
    display_name: str = ""
    faction: Faction = Faction.VILLAGER
    has_night_action: bool = False
    action_phase: GamePhase | None = None
    priority: int = 100  # lower = resolved earlier

    # ── abstract interface ───────────────────────────────────

    @abstractmethod
    def get_action_types(self) -> list[ActionType]:
        """Return the action types this role can perform."""
        ...

    @abstractmethod
    def can_act(self, phase: GamePhase, *, is_alive: bool = True, **kwargs: Any) -> bool:
        """Return True if the role can act in the given phase."""
        ...

    def on_death(self, cause: str, **kwargs: Any) -> dict[str, Any] | None:
        """Hook called when the player with this role dies.

        Return a dict of side-effects (e.g. hunter trigger) or None.
        """
        return None
