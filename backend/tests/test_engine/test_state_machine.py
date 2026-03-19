"""Tests for the game state machine."""

import pytest

from app.engine.state_machine import GameContext, GamePhase, PhaseResult, StateMachine, PHASE_TIMEOUTS


class TestStateMachineBasic:
    """Basic state machine lifecycle tests."""

    def test_initial_state(self):
        sm = StateMachine()
        assert sm.phase == GamePhase.WAITING
        assert sm.round_number == 0

    def test_waiting_to_role_assignment(self):
        sm = StateMachine()
        ctx = GameContext(alive_roles={"werewolf", "seer", "witch", "villager"})
        result = sm.advance(ctx)
        assert result.previous_phase == GamePhase.WAITING
        assert result.current_phase == GamePhase.ROLE_ASSIGNMENT

    def test_role_assignment_starts_round_1(self):
        sm = StateMachine(phase=GamePhase.ROLE_ASSIGNMENT)
        ctx = GameContext(alive_roles={"werewolf", "seer", "witch", "villager"})
        result = sm.advance(ctx)
        assert result.current_phase == GamePhase.NIGHT_START
        assert sm.round_number == 1

    def test_game_over_raises(self):
        sm = StateMachine(phase=GamePhase.GAME_OVER)
        ctx = GameContext()
        with pytest.raises(RuntimeError, match="already over"):
            sm.advance(ctx)

    def test_force_phase(self):
        sm = StateMachine()
        sm.force_phase(GamePhase.DAY_VOTE, round_number=3)
        assert sm.phase == GamePhase.DAY_VOTE
        assert sm.round_number == 3


class TestNightFlow:
    """Night phase flow with all roles alive."""

    def _ctx_all_alive(self) -> GameContext:
        return GameContext(alive_roles={"werewolf", "seer", "witch", "hunter", "guard", "villager"})

    def test_night_full_flow(self):
        sm = StateMachine(phase=GamePhase.NIGHT_START, round_number=1)
        ctx = self._ctx_all_alive()

        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.NIGHT_WEREWOLF

        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.NIGHT_SEER

        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.NIGHT_WITCH

        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.NIGHT_END

    def test_skip_seer_when_dead(self):
        sm = StateMachine(phase=GamePhase.NIGHT_WEREWOLF, round_number=1)
        ctx = GameContext(alive_roles={"werewolf", "witch", "villager"})  # no seer
        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.NIGHT_WITCH

    def test_skip_witch_when_dead(self):
        sm = StateMachine(phase=GamePhase.NIGHT_SEER, round_number=1)
        ctx = GameContext(alive_roles={"werewolf", "seer", "villager"})  # no witch
        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.NIGHT_END

    def test_skip_both_seer_and_witch(self):
        sm = StateMachine(phase=GamePhase.NIGHT_WEREWOLF, round_number=1)
        ctx = GameContext(alive_roles={"werewolf", "villager"})
        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.NIGHT_END

    def test_witch_poisons_hunter_triggers_night_hunter(self):
        sm = StateMachine(phase=GamePhase.NIGHT_WITCH, round_number=1)
        ctx = GameContext(
            alive_roles={"werewolf", "witch", "hunter", "villager"},
            witch_poisoned_hunter=True,
        )
        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.NIGHT_HUNTER

    def test_night_hunter_to_night_end(self):
        sm = StateMachine(phase=GamePhase.NIGHT_HUNTER, round_number=1)
        ctx = GameContext(alive_roles={"werewolf", "villager"})
        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.NIGHT_END


class TestDayFlow:
    """Day phase flow."""

    def test_day_full_flow(self):
        sm = StateMachine(phase=GamePhase.NIGHT_END, round_number=1)
        ctx = GameContext(alive_roles={"werewolf", "seer", "villager"})

        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.DAY_ANNOUNCEMENT

        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.DAY_SPEECH

        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.DAY_VOTE

        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.DAY_VOTE_RESULT

    def test_vote_killed_hunter_triggers_shoot(self):
        sm = StateMachine(phase=GamePhase.DAY_VOTE_RESULT, round_number=1)
        ctx = GameContext(
            alive_roles={"werewolf", "hunter", "villager"},
            vote_killed_hunter=True,
        )
        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.HUNTER_SHOOT

    def test_hunter_shoot_to_last_words(self):
        sm = StateMachine(phase=GamePhase.HUNTER_SHOOT, round_number=1)
        ctx = GameContext(alive_roles={"werewolf", "villager"})
        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.LAST_WORDS

    def test_last_words_to_night_increments_round(self):
        sm = StateMachine(phase=GamePhase.LAST_WORDS, round_number=1)
        ctx = GameContext(alive_roles={"werewolf", "seer", "villager"})
        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.NIGHT_START
        assert sm.round_number == 2


class TestGameOver:
    """Game over detection at multiple checkpoints."""

    def test_game_over_at_day_announcement(self):
        sm = StateMachine(phase=GamePhase.DAY_ANNOUNCEMENT, round_number=1)
        ctx = GameContext(
            alive_roles=set(),
            game_over=True,
            winner="villager",
            win_reason="All werewolves dead",
        )
        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.GAME_OVER
        assert r.data["winner"] == "villager"

    def test_game_over_at_last_words(self):
        sm = StateMachine(phase=GamePhase.LAST_WORDS, round_number=2)
        ctx = GameContext(
            game_over=True,
            winner="werewolf",
            win_reason="Werewolves dominate",
        )
        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.GAME_OVER

    def test_game_over_before_night(self):
        """game_over flag can trigger from any phase."""
        sm = StateMachine(phase=GamePhase.NIGHT_START, round_number=1)
        ctx = GameContext(game_over=True, winner="werewolf", win_reason="test")
        r = sm.advance(ctx)
        assert r.current_phase == GamePhase.GAME_OVER


class TestFullGameFlow:
    """Simulate a multi-round game flow."""

    def test_two_round_game(self):
        sm = StateMachine()
        ctx = GameContext(alive_roles={"werewolf", "seer", "witch", "hunter", "villager"})

        expected = [
            GamePhase.ROLE_ASSIGNMENT,
            GamePhase.NIGHT_START,
            GamePhase.NIGHT_WEREWOLF,
            GamePhase.NIGHT_SEER,
            GamePhase.NIGHT_WITCH,
            GamePhase.NIGHT_END,
            GamePhase.DAY_ANNOUNCEMENT,
            GamePhase.DAY_SPEECH,
            GamePhase.DAY_VOTE,
            GamePhase.DAY_VOTE_RESULT,
            GamePhase.LAST_WORDS,
            # Round 2
            GamePhase.NIGHT_START,
            GamePhase.NIGHT_WEREWOLF,
            GamePhase.NIGHT_SEER,
            GamePhase.NIGHT_WITCH,
            GamePhase.NIGHT_END,
            GamePhase.DAY_ANNOUNCEMENT,
            GamePhase.DAY_SPEECH,
            GamePhase.DAY_VOTE,
            GamePhase.DAY_VOTE_RESULT,
            GamePhase.LAST_WORDS,
        ]

        for exp_phase in expected:
            r = sm.advance(ctx)
            assert r.current_phase == exp_phase, f"Expected {exp_phase}, got {r.current_phase}"

        # Round was set to 1 in ROLE_ASSIGNMENT.
        # First LAST_WORDS → NIGHT_START incremented to 2.
        # We ended on the second LAST_WORDS (haven't advanced from it yet).
        assert sm.round_number == 2

    def test_phase_timeouts_all_defined(self):
        """Every phase should have a timeout entry."""
        for phase in GamePhase:
            assert phase in PHASE_TIMEOUTS, f"Missing timeout for {phase}"
