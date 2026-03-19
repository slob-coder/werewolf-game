"""Tests for InformationFilter and ContentFilter."""

import pytest

from app.engine.information_filter import (
    ContentCheckResult,
    ContentFilter,
    InformationFilter,
    PlayerContext,
)
from app.roles.base import Faction


@pytest.fixture
def info_filter():
    return InformationFilter()


@pytest.fixture
def sample_players():
    """6-player game: 2 werewolves (seats 1,2), 2 villagers (3,4), seer (5), witch (6)."""
    return [
        {"seat": 1, "agent_name": "Wolf1", "is_alive": True, "role": "werewolf", "faction": Faction.WEREWOLF},
        {"seat": 2, "agent_name": "Wolf2", "is_alive": True, "role": "werewolf", "faction": Faction.WEREWOLF},
        {"seat": 3, "agent_name": "Villager1", "is_alive": True, "role": "villager", "faction": Faction.VILLAGER},
        {"seat": 4, "agent_name": "Villager2", "is_alive": False, "role": "villager", "faction": Faction.VILLAGER},
        {"seat": 5, "agent_name": "Seer1", "is_alive": True, "role": "seer", "faction": Faction.GOD},
        {"seat": 6, "agent_name": "Witch1", "is_alive": False, "role": "witch", "faction": Faction.GOD},
    ]


# ── Game state filtering tests ───────────────────────────────────


class TestGameStateFilter:
    def test_werewolf_sees_teammate_roles(self, info_filter, sample_players):
        """Werewolf at seat 1 should see the role of werewolf at seat 2."""
        ctx = PlayerContext(seat=1, role="werewolf", faction=Faction.WEREWOLF, is_alive=True)
        filtered = info_filter.filter_game_state(sample_players, ctx)

        # Self and teammate visible
        assert filtered[0]["role"] == "werewolf"  # self (seat 1)
        assert filtered[1]["role"] == "werewolf"  # teammate (seat 2)
        # Others hidden
        assert filtered[2]["role"] is None  # villager
        assert filtered[4]["role"] is None  # seer

    def test_villager_sees_only_own_role(self, info_filter, sample_players):
        """Villager at seat 3 sees only their own role."""
        ctx = PlayerContext(seat=3, role="villager", faction=Faction.VILLAGER, is_alive=True)
        filtered = info_filter.filter_game_state(sample_players, ctx)

        assert filtered[2]["role"] == "villager"  # self
        assert filtered[0]["role"] is None  # werewolf hidden
        assert filtered[4]["role"] is None  # seer hidden

    def test_god_faction_sees_only_own_role(self, info_filter, sample_players):
        """Seer (god faction) at seat 5 sees only their own role."""
        ctx = PlayerContext(seat=5, role="seer", faction=Faction.GOD, is_alive=True)
        filtered = info_filter.filter_game_state(sample_players, ctx)

        assert filtered[4]["role"] == "seer"  # self
        assert filtered[0]["role"] is None  # werewolf hidden

    def test_dead_player_sees_other_dead_roles(self, info_filter, sample_players):
        """Dead villager at seat 4 can see dead witch at seat 6's role."""
        ctx = PlayerContext(seat=4, role="villager", faction=Faction.VILLAGER, is_alive=False)
        filtered = info_filter.filter_game_state(sample_players, ctx)

        assert filtered[3]["role"] == "villager"  # self
        assert filtered[5]["role"] == "witch"  # dead witch visible to dead player
        assert filtered[0]["role"] is None  # alive werewolf still hidden

    def test_spectator_sees_all(self, info_filter, sample_players):
        """Spectator (god view) sees all roles."""
        ctx = PlayerContext(
            seat=0, role="spectator", faction="none",
            is_alive=False, is_spectator=True,
        )
        filtered = info_filter.filter_game_state(sample_players, ctx)

        for p in filtered:
            assert p["role"] is not None


# ── Event filtering tests ────────────────────────────────────────


class TestEventFilter:
    def test_public_event_visible_to_all(self, info_filter):
        event = {"event_type": "day_announcement", "data": {}, "visibility": "public"}
        ctx = PlayerContext(seat=3, role="villager", faction=Faction.VILLAGER, is_alive=True)
        assert info_filter.filter_event(event, ctx) is not None

    def test_god_event_hidden_from_players(self, info_filter):
        event = {"event_type": "debug", "data": {}, "visibility": "god"}
        ctx = PlayerContext(seat=1, role="werewolf", faction=Faction.WEREWOLF, is_alive=True)
        assert info_filter.filter_event(event, ctx) is None

    def test_god_event_visible_to_spectator(self, info_filter):
        event = {"event_type": "debug", "data": {}, "visibility": "god"}
        ctx = PlayerContext(seat=0, role="spectator", faction="none", is_alive=False, is_spectator=True)
        assert info_filter.filter_event(event, ctx) is not None

    def test_private_event_visible_to_actor(self, info_filter):
        event = {
            "event_type": "seer_result",
            "data": {"actor_seat": 5, "target_seat": 1, "result": "werewolf"},
            "visibility": "private",
        }
        ctx = PlayerContext(seat=5, role="seer", faction=Faction.GOD, is_alive=True)
        assert info_filter.filter_event(event, ctx) is not None

    def test_private_event_hidden_from_others(self, info_filter):
        event = {
            "event_type": "seer_result",
            "data": {"actor_seat": 5, "target_seat": 1, "result": "werewolf"},
            "visibility": "private",
        }
        ctx = PlayerContext(seat=3, role="villager", faction=Faction.VILLAGER, is_alive=True)
        assert info_filter.filter_event(event, ctx) is None

    def test_role_event_visible_to_same_faction(self, info_filter):
        event = {
            "event_type": "werewolf_kill_choice",
            "data": {"faction": Faction.WEREWOLF, "target_seat": 3},
            "visibility": "role",
        }
        ctx = PlayerContext(seat=2, role="werewolf", faction=Faction.WEREWOLF, is_alive=True)
        assert info_filter.filter_event(event, ctx) is not None

    def test_role_event_hidden_from_other_faction(self, info_filter):
        event = {
            "event_type": "werewolf_kill_choice",
            "data": {"faction": Faction.WEREWOLF, "target_seat": 3},
            "visibility": "role",
        }
        ctx = PlayerContext(seat=3, role="villager", faction=Faction.VILLAGER, is_alive=True)
        assert info_filter.filter_event(event, ctx) is None

    def test_role_event_visible_to_dead_player(self, info_filter):
        """Dead players see role-level events."""
        event = {
            "event_type": "werewolf_kill_choice",
            "data": {"faction": Faction.WEREWOLF, "target_seat": 3},
            "visibility": "role",
        }
        ctx = PlayerContext(seat=3, role="villager", faction=Faction.VILLAGER, is_alive=False)
        assert info_filter.filter_event(event, ctx) is not None

    def test_bulk_filter_events(self, info_filter):
        events = [
            {"event_type": "public_ev", "data": {}, "visibility": "public"},
            {"event_type": "god_ev", "data": {}, "visibility": "god"},
            {"event_type": "private_ev", "data": {"actor_seat": 5}, "visibility": "private"},
        ]
        ctx = PlayerContext(seat=5, role="seer", faction=Faction.GOD, is_alive=True)
        filtered = info_filter.filter_events(events, ctx)
        # public visible, god hidden, private visible (actor_seat matches)
        assert len(filtered) == 2
        types = {e["event_type"] for e in filtered}
        assert "public_ev" in types
        assert "private_ev" in types
        assert "god_ev" not in types


# ── Content filter tests ─────────────────────────────────────────


class TestContentFilter:
    def test_normal_content_passes(self):
        result = ContentFilter.check("我觉得3号是狼人！", "villager")
        assert result.passed

    def test_empty_content_passes(self):
        result = ContentFilter.check("", "villager")
        assert result.passed

    def test_forbidden_pattern_fails(self):
        result = ContentFilter.check("event_type is phase.night data", "villager")
        assert not result.passed
        assert "forbidden pattern" in result.reason.lower()

    def test_api_key_pattern_fails(self):
        result = ContentFilter.check("My api_key is abc123", "werewolf")
        assert not result.passed

    def test_x_agent_key_pattern_fails(self):
        result = ContentFilter.check("Send X-Agent-Key header", "werewolf")
        assert not result.passed

    def test_long_content_fails(self):
        result = ContentFilter.check("x" * 5001, "villager")
        assert not result.passed
        assert "maximum length" in result.reason.lower()

    def test_action_type_werewolf_kill_pattern_fails(self):
        result = ContentFilter.check("action_type werewolf_kill sent to target", "villager")
        assert not result.passed
