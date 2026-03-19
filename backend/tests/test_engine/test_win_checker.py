"""Tests for the win checker."""

import pytest

from app.engine.win_checker import PlayerInfo, WinChecker, WinResult
from app.roles.base import Faction


@pytest.fixture
def checker():
    return WinChecker()


def _make_players(specs: list[tuple[int, str, Faction, bool]]) -> list[PlayerInfo]:
    return [PlayerInfo(seat=s, role_name=r, faction=f, is_alive=a) for s, r, f, a in specs]


class TestGoodWins:
    def test_all_werewolves_dead(self, checker):
        players = _make_players([
            (1, "werewolf", Faction.WEREWOLF, False),
            (2, "werewolf", Faction.WEREWOLF, False),
            (3, "seer", Faction.GOD, True),
            (4, "villager", Faction.VILLAGER, True),
            (5, "villager", Faction.VILLAGER, True),
        ])
        result = checker.check(players)
        assert result is not None
        assert result.winner == "villager"

    def test_all_werewolves_dead_some_good_dead(self, checker):
        players = _make_players([
            (1, "werewolf", Faction.WEREWOLF, False),
            (2, "werewolf", Faction.WEREWOLF, False),
            (3, "seer", Faction.GOD, False),
            (4, "villager", Faction.VILLAGER, True),
        ])
        result = checker.check(players)
        assert result is not None
        assert result.winner == "villager"


class TestWerewolfWins:
    def test_equal_numbers(self, checker):
        players = _make_players([
            (1, "werewolf", Faction.WEREWOLF, True),
            (2, "werewolf", Faction.WEREWOLF, True),
            (3, "seer", Faction.GOD, True),
            (4, "villager", Faction.VILLAGER, True),
        ])
        result = checker.check(players)
        assert result is not None
        assert result.winner == "werewolf"

    def test_werewolves_outnumber(self, checker):
        players = _make_players([
            (1, "werewolf", Faction.WEREWOLF, True),
            (2, "werewolf", Faction.WEREWOLF, True),
            (3, "villager", Faction.VILLAGER, True),
        ])
        result = checker.check(players)
        assert result is not None
        assert result.winner == "werewolf"


class TestGameContinues:
    def test_good_advantage(self, checker):
        players = _make_players([
            (1, "werewolf", Faction.WEREWOLF, True),
            (2, "seer", Faction.GOD, True),
            (3, "villager", Faction.VILLAGER, True),
            (4, "villager", Faction.VILLAGER, True),
        ])
        result = checker.check(players)
        assert result is None

    def test_standard_9_start(self, checker):
        players = _make_players([
            (1, "werewolf", Faction.WEREWOLF, True),
            (2, "werewolf", Faction.WEREWOLF, True),
            (3, "werewolf", Faction.WEREWOLF, True),
            (4, "seer", Faction.GOD, True),
            (5, "witch", Faction.GOD, True),
            (6, "hunter", Faction.GOD, True),
            (7, "villager", Faction.VILLAGER, True),
            (8, "villager", Faction.VILLAGER, True),
            (9, "villager", Faction.VILLAGER, True),
        ])
        result = checker.check(players)
        assert result is None


class TestEdgeCases:
    def test_everyone_dead(self, checker):
        """If somehow all die at once, werewolves = 0 → good wins."""
        players = _make_players([
            (1, "werewolf", Faction.WEREWOLF, False),
            (2, "villager", Faction.VILLAGER, False),
        ])
        result = checker.check(players)
        assert result is not None
        assert result.winner == "villager"

    def test_single_werewolf_single_good(self, checker):
        """1 wolf == 1 good → wolf wins."""
        players = _make_players([
            (1, "werewolf", Faction.WEREWOLF, True),
            (2, "villager", Faction.VILLAGER, True),
        ])
        result = checker.check(players)
        assert result is not None
        assert result.winner == "werewolf"
