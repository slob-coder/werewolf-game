"""Tests for the night resolver."""

import pytest

from app.engine.night_resolver import NightAction, NightResolver, NightResult
from app.roles.base import ActionType


@pytest.fixture
def resolver():
    return NightResolver()


@pytest.fixture
def alive_seats():
    return {1, 2, 3, 4, 5, 6, 7, 8, 9}


@pytest.fixture
def seat_roles():
    return {
        1: "werewolf", 2: "werewolf", 3: "werewolf",
        4: "seer", 5: "witch", 6: "hunter",
        7: "villager", 8: "villager", 9: "villager",
    }


class TestBasicKill:
    def test_werewolf_kill(self, resolver, alive_seats, seat_roles):
        actions = [
            NightAction(actor_seat=1, role="werewolf", action_type=ActionType.WEREWOLF_KILL, target_seat=4),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert 4 in result.killed
        assert len(result.saved) == 0

    def test_no_kill_if_no_action(self, resolver, alive_seats, seat_roles):
        actions = []
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert len(result.killed) == 0


class TestGuardProtection:
    def test_guard_saves_target(self, resolver, alive_seats, seat_roles):
        actions = [
            NightAction(actor_seat=8, role="guard", action_type=ActionType.GUARD_PROTECT, target_seat=4),
            NightAction(actor_seat=1, role="werewolf", action_type=ActionType.WEREWOLF_KILL, target_seat=4),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert 4 not in result.killed
        assert 4 in result.saved

    def test_guard_wrong_target(self, resolver, alive_seats, seat_roles):
        actions = [
            NightAction(actor_seat=8, role="guard", action_type=ActionType.GUARD_PROTECT, target_seat=7),
            NightAction(actor_seat=1, role="werewolf", action_type=ActionType.WEREWOLF_KILL, target_seat=4),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert 4 in result.killed
        assert 7 in result.protected


class TestWitchSave:
    def test_witch_saves_target(self, resolver, alive_seats, seat_roles):
        actions = [
            NightAction(actor_seat=1, role="werewolf", action_type=ActionType.WEREWOLF_KILL, target_seat=4),
            NightAction(actor_seat=5, role="witch", action_type=ActionType.WITCH_SAVE),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert 4 not in result.killed
        assert 4 in result.saved

    def test_witch_poison(self, resolver, alive_seats, seat_roles):
        actions = [
            NightAction(actor_seat=1, role="werewolf", action_type=ActionType.WEREWOLF_KILL, target_seat=4),
            NightAction(actor_seat=5, role="witch", action_type=ActionType.WITCH_POISON, target_seat=7),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert 4 in result.killed
        assert 7 in result.killed
        assert 7 in result.poisoned

    def test_witch_skip(self, resolver, alive_seats, seat_roles):
        actions = [
            NightAction(actor_seat=1, role="werewolf", action_type=ActionType.WEREWOLF_KILL, target_seat=4),
            NightAction(actor_seat=5, role="witch", action_type=ActionType.WITCH_SKIP),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert 4 in result.killed


class TestGuardWitchConflict:
    def test_same_guard_save_default_survives(self, resolver, alive_seats, seat_roles):
        """Default config: both guard and witch protect → target survives."""
        actions = [
            NightAction(actor_seat=8, role="guard", action_type=ActionType.GUARD_PROTECT, target_seat=4),
            NightAction(actor_seat=1, role="werewolf", action_type=ActionType.WEREWOLF_KILL, target_seat=4),
            NightAction(actor_seat=5, role="witch", action_type=ActionType.WITCH_SAVE),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert 4 not in result.killed
        assert 4 in result.saved

    def test_same_guard_save_dies_config(self, alive_seats, seat_roles):
        """When configured, both guard and witch protect → target dies."""
        resolver = NightResolver(same_guard_save_dies=True)
        actions = [
            NightAction(actor_seat=8, role="guard", action_type=ActionType.GUARD_PROTECT, target_seat=4),
            NightAction(actor_seat=1, role="werewolf", action_type=ActionType.WEREWOLF_KILL, target_seat=4),
            NightAction(actor_seat=5, role="witch", action_type=ActionType.WITCH_SAVE),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert 4 in result.killed


class TestSeerCheck:
    def test_check_werewolf(self, resolver, alive_seats, seat_roles):
        actions = [
            NightAction(actor_seat=4, role="seer", action_type=ActionType.SEER_CHECK, target_seat=1),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert result.seer_results[1] == "werewolf"

    def test_check_good_player(self, resolver, alive_seats, seat_roles):
        actions = [
            NightAction(actor_seat=4, role="seer", action_type=ActionType.SEER_CHECK, target_seat=7),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert result.seer_results[7] == "good"

    def test_check_god_shows_good(self, resolver, alive_seats, seat_roles):
        actions = [
            NightAction(actor_seat=4, role="seer", action_type=ActionType.SEER_CHECK, target_seat=5),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert result.seer_results[5] == "good"  # witch is "good"


class TestComplexScenario:
    def test_kill_and_poison_different_targets(self, resolver, alive_seats, seat_roles):
        actions = [
            NightAction(actor_seat=1, role="werewolf", action_type=ActionType.WEREWOLF_KILL, target_seat=4),
            NightAction(actor_seat=5, role="witch", action_type=ActionType.WITCH_POISON, target_seat=7),
            NightAction(actor_seat=4, role="seer", action_type=ActionType.SEER_CHECK, target_seat=2),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert 4 in result.killed
        assert 7 in result.killed
        assert result.seer_results[2] == "werewolf"

    def test_poison_same_as_kill_target(self, resolver, alive_seats, seat_roles):
        """If witch poisons the same target werewolves killed, they only die once."""
        actions = [
            NightAction(actor_seat=1, role="werewolf", action_type=ActionType.WEREWOLF_KILL, target_seat=7),
            NightAction(actor_seat=5, role="witch", action_type=ActionType.WITCH_POISON, target_seat=7),
        ]
        result = resolver.resolve(actions, alive_seats, seat_roles)
        assert result.killed.count(7) == 1  # deduped
        assert 7 in result.poisoned
