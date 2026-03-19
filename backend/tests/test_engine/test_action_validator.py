"""Tests for the action validator."""

import pytest

from app.engine.action_validator import ActionValidator
from app.engine.state_machine import GamePhase
from app.roles import Werewolf, Seer, Witch, Hunter, Guard, Villager
from app.roles.base import ActionType


@pytest.fixture
def validator():
    return ActionValidator()


@pytest.fixture
def alive_seats():
    return {1, 2, 3, 4, 5, 6, 7, 8, 9}


class TestPhaseValidation:
    def test_werewolf_kill_correct_phase(self, validator, alive_seats):
        result = validator.validate(
            ActionType.WEREWOLF_KILL, 1, Werewolf(),
            GamePhase.NIGHT_WEREWOLF,
            target_seat=4, alive_seats=alive_seats,
        )
        assert result.valid is True

    def test_werewolf_kill_wrong_phase(self, validator, alive_seats):
        result = validator.validate(
            ActionType.WEREWOLF_KILL, 1, Werewolf(),
            GamePhase.DAY_VOTE,
            target_seat=4, alive_seats=alive_seats,
        )
        assert result.valid is False
        assert "not allowed in phase" in result.reason

    def test_seer_check_correct_phase(self, validator, alive_seats):
        result = validator.validate(
            ActionType.SEER_CHECK, 4, Seer(),
            GamePhase.NIGHT_SEER,
            target_seat=1, alive_seats=alive_seats,
        )
        assert result.valid is True


class TestDeadPlayer:
    def test_dead_player_cannot_act(self, validator, alive_seats):
        result = validator.validate(
            ActionType.WEREWOLF_KILL, 1, Werewolf(),
            GamePhase.NIGHT_WEREWOLF,
            is_alive=False, target_seat=4, alive_seats=alive_seats,
        )
        assert result.valid is False
        assert "dead" in result.reason.lower()

    def test_dead_player_can_say_last_words(self, validator):
        result = validator.validate(
            ActionType.LAST_WORDS, 4, Seer(),
            GamePhase.LAST_WORDS,
            is_alive=False,
        )
        assert result.valid is True

    def test_dead_hunter_can_shoot(self, validator, alive_seats):
        result = validator.validate(
            ActionType.HUNTER_SHOOT, 6, Hunter(),
            GamePhase.HUNTER_SHOOT,
            is_alive=False, target_seat=1, alive_seats=alive_seats,
        )
        assert result.valid is True


class TestRoleCapability:
    def test_villager_cannot_kill(self, validator, alive_seats):
        result = validator.validate(
            ActionType.WEREWOLF_KILL, 7, Villager(),
            GamePhase.NIGHT_WEREWOLF,
            target_seat=4, alive_seats=alive_seats,
        )
        assert result.valid is False
        assert "cannot perform" in result.reason.lower()

    def test_seer_cannot_poison(self, validator, alive_seats):
        result = validator.validate(
            ActionType.WITCH_POISON, 4, Seer(),
            GamePhase.NIGHT_WITCH,
            target_seat=1, alive_seats=alive_seats,
        )
        assert result.valid is False


class TestTargetValidation:
    def test_missing_target(self, validator, alive_seats):
        result = validator.validate(
            ActionType.WEREWOLF_KILL, 1, Werewolf(),
            GamePhase.NIGHT_WEREWOLF,
            alive_seats=alive_seats,
        )
        assert result.valid is False
        assert "target is required" in result.reason.lower()

    def test_dead_target(self, validator):
        result = validator.validate(
            ActionType.WEREWOLF_KILL, 1, Werewolf(),
            GamePhase.NIGHT_WEREWOLF,
            target_seat=4, alive_seats={1, 2, 3},
        )
        assert result.valid is False
        assert "not alive" in result.reason.lower()

    def test_self_target_kill(self, validator, alive_seats):
        result = validator.validate(
            ActionType.WEREWOLF_KILL, 1, Werewolf(),
            GamePhase.NIGHT_WEREWOLF,
            target_seat=1, alive_seats=alive_seats,
        )
        assert result.valid is False
        assert "cannot target self" in result.reason.lower()


class TestDuplicateAction:
    def test_duplicate_rejected(self, validator, alive_seats):
        result = validator.validate(
            ActionType.WEREWOLF_KILL, 1, Werewolf(),
            GamePhase.NIGHT_WEREWOLF,
            target_seat=4, alive_seats=alive_seats,
            already_acted=True,
        )
        assert result.valid is False
        assert "already acted" in result.reason.lower()

    def test_chat_not_blocked_by_duplicate(self, validator):
        result = validator.validate(
            ActionType.WEREWOLF_CHAT, 1, Werewolf(),
            GamePhase.NIGHT_WEREWOLF,
            already_acted=True,
        )
        assert result.valid is True


class TestRoleSpecificChecks:
    def test_witch_no_save_potion(self, validator):
        result = validator.validate(
            ActionType.WITCH_SAVE, 5, Witch(),
            GamePhase.NIGHT_WITCH,
            extra={"has_save_potion": False},
        )
        assert result.valid is False
        assert "save potion" in result.reason.lower()

    def test_witch_no_poison_potion(self, validator, alive_seats):
        result = validator.validate(
            ActionType.WITCH_POISON, 5, Witch(),
            GamePhase.NIGHT_WITCH,
            target_seat=1, alive_seats=alive_seats,
            extra={"has_poison_potion": False},
        )
        assert result.valid is False
        assert "poison potion" in result.reason.lower()

    def test_guard_consecutive_protection(self, validator, alive_seats):
        result = validator.validate(
            ActionType.GUARD_PROTECT, 8, Guard(),
            GamePhase.NIGHT_WEREWOLF,
            target_seat=3, alive_seats=alive_seats,
            extra={"last_protected_seat": 3},
        )
        assert result.valid is False
        assert "same target" in result.reason.lower()

    def test_guard_different_target_ok(self, validator, alive_seats):
        result = validator.validate(
            ActionType.GUARD_PROTECT, 8, Guard(),
            GamePhase.NIGHT_WEREWOLF,
            target_seat=5, alive_seats=alive_seats,
            extra={"last_protected_seat": 3},
        )
        assert result.valid is True

    def test_idiot_no_vote(self, validator, alive_seats):
        result = validator.validate(
            ActionType.VOTE, 9, Villager(),
            GamePhase.DAY_VOTE,
            target_seat=1, alive_seats=alive_seats,
            extra={"can_vote": False},
        )
        assert result.valid is False
        assert "lost voting rights" in result.reason.lower()


class TestUniversalActions:
    def test_speech_any_role(self, validator):
        result = validator.validate(
            ActionType.SPEECH, 7, Villager(),
            GamePhase.DAY_SPEECH,
        )
        assert result.valid is True

    def test_vote_any_role(self, validator, alive_seats):
        result = validator.validate(
            ActionType.VOTE, 7, Villager(),
            GamePhase.DAY_VOTE,
            target_seat=1, alive_seats=alive_seats,
        )
        assert result.valid is True

    def test_vote_abstain(self, validator):
        result = validator.validate(
            ActionType.VOTE_ABSTAIN, 7, Villager(),
            GamePhase.DAY_VOTE,
        )
        assert result.valid is True
