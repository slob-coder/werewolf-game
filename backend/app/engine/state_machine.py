"""Game state machine — drives phase transitions for a werewolf game."""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


class GamePhase(str, enum.Enum):
    """All possible game phases."""

    WAITING = "waiting"
    ROLE_ASSIGNMENT = "role_assignment"
    NIGHT_START = "night_start"
    NIGHT_WEREWOLF = "night_werewolf"
    NIGHT_SEER = "night_seer"
    NIGHT_WITCH = "night_witch"
    NIGHT_HUNTER = "night_hunter"
    NIGHT_END = "night_end"
    DAY_ANNOUNCEMENT = "day_announcement"
    DAY_SPEECH = "day_speech"
    DAY_VOTE = "day_vote"
    DAY_VOTE_RESULT = "day_vote_result"
    HUNTER_SHOOT = "hunter_shoot"
    LAST_WORDS = "last_words"
    GAME_OVER = "game_over"


# Default timeout in seconds per phase
PHASE_TIMEOUTS: dict[GamePhase, int] = {
    GamePhase.WAITING: 0,  # no auto-advance
    GamePhase.ROLE_ASSIGNMENT: 5,
    GamePhase.NIGHT_START: 3,
    GamePhase.NIGHT_WEREWOLF: 60,
    GamePhase.NIGHT_SEER: 30,
    GamePhase.NIGHT_WITCH: 30,
    GamePhase.NIGHT_HUNTER: 30,
    GamePhase.NIGHT_END: 3,
    GamePhase.DAY_ANNOUNCEMENT: 5,
    GamePhase.DAY_SPEECH: 90,  # per player – scheduler multiplies
    GamePhase.DAY_VOTE: 60,
    GamePhase.DAY_VOTE_RESULT: 5,
    GamePhase.HUNTER_SHOOT: 30,
    GamePhase.LAST_WORDS: 30,
    GamePhase.GAME_OVER: 0,
}


@dataclass
class PhaseResult:
    """Result returned after a phase transition."""

    previous_phase: GamePhase
    current_phase: GamePhase
    round_number: int
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameContext:
    """Lightweight snapshot of game state used by the state machine for
    conditional transitions (e.g. skip witch phase if witch is dead)."""

    alive_roles: set[str] = field(default_factory=set)
    witch_poisoned_hunter: bool = False
    hunter_pending_shot: bool = False
    vote_killed_hunter: bool = False
    game_over: bool = False
    winner: str | None = None
    win_reason: str | None = None


class StateMachine:
    """Deterministic state machine that manages game phase flow.

    The machine itself is *pure logic* — it does not interact with DB or
    network.  The ``GameEngine`` (or tests) feed it a ``GameContext`` and
    call ``advance()`` to get the next phase.
    """

    def __init__(self, phase: GamePhase = GamePhase.WAITING, round_number: int = 0):
        self._phase = phase
        self._round = round_number

    # ── properties ────────────────────────────────────────────

    @property
    def phase(self) -> GamePhase:
        return self._phase

    @property
    def round_number(self) -> int:
        return self._round

    def get_timeout(self) -> int:
        return PHASE_TIMEOUTS.get(self._phase, 30)

    # ── core transition ──────────────────────────────────────

    def advance(self, ctx: GameContext) -> PhaseResult:
        """Advance to the next phase based on *ctx*.

        Returns a ``PhaseResult`` describing the transition.  Raises
        ``RuntimeError`` if the game is already over.
        """
        if self._phase == GamePhase.GAME_OVER:
            raise RuntimeError("Game is already over, cannot advance")

        prev = self._phase
        next_phase = self._next_phase(ctx)
        self._phase = next_phase

        data: dict[str, Any] = {}
        if next_phase == GamePhase.GAME_OVER:
            data["winner"] = ctx.winner
            data["win_reason"] = ctx.win_reason

        return PhaseResult(
            previous_phase=prev,
            current_phase=next_phase,
            round_number=self._round,
            data=data,
        )

    def force_phase(self, phase: GamePhase, round_number: int | None = None) -> None:
        """Force the machine into a specific phase (for recovery / tests)."""
        self._phase = phase
        if round_number is not None:
            self._round = round_number

    # ── private helpers ──────────────────────────────────────

    def _next_phase(self, ctx: GameContext) -> GamePhase:  # noqa: C901
        """Compute the next phase given the current context."""
        p = self._phase

        if ctx.game_over:
            return GamePhase.GAME_OVER

        if p == GamePhase.WAITING:
            return GamePhase.ROLE_ASSIGNMENT

        if p == GamePhase.ROLE_ASSIGNMENT:
            self._round = 1
            return GamePhase.NIGHT_START

        if p == GamePhase.NIGHT_START:
            return GamePhase.NIGHT_WEREWOLF

        if p == GamePhase.NIGHT_WEREWOLF:
            if "seer" in ctx.alive_roles:
                return GamePhase.NIGHT_SEER
            # skip seer if dead, fall through
            return self._after_seer(ctx)

        if p == GamePhase.NIGHT_SEER:
            return self._after_seer(ctx)

        if p == GamePhase.NIGHT_WITCH:
            if ctx.witch_poisoned_hunter and "hunter" in ctx.alive_roles:
                return GamePhase.NIGHT_HUNTER
            return GamePhase.NIGHT_END

        if p == GamePhase.NIGHT_HUNTER:
            return GamePhase.NIGHT_END

        if p == GamePhase.NIGHT_END:
            return GamePhase.DAY_ANNOUNCEMENT

        if p == GamePhase.DAY_ANNOUNCEMENT:
            if ctx.game_over:
                return GamePhase.GAME_OVER
            return GamePhase.DAY_SPEECH

        if p == GamePhase.DAY_SPEECH:
            return GamePhase.DAY_VOTE

        if p == GamePhase.DAY_VOTE:
            return GamePhase.DAY_VOTE_RESULT

        if p == GamePhase.DAY_VOTE_RESULT:
            if ctx.vote_killed_hunter and "hunter" in ctx.alive_roles:
                return GamePhase.HUNTER_SHOOT
            return GamePhase.LAST_WORDS

        if p == GamePhase.HUNTER_SHOOT:
            return GamePhase.LAST_WORDS

        if p == GamePhase.LAST_WORDS:
            if ctx.game_over:
                return GamePhase.GAME_OVER
            self._round += 1
            return GamePhase.NIGHT_START

        # Fallback (should never happen)
        raise RuntimeError(f"No transition defined from {p}")

    def _after_seer(self, ctx: GameContext) -> GamePhase:
        if "witch" in ctx.alive_roles:
            return GamePhase.NIGHT_WITCH
        # witch dead — check if hunter triggered by poison (not possible if
        # witch is dead, so skip directly)
        return GamePhase.NIGHT_END
