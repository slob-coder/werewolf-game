"""Tests for RoomManager — CRUD, join/leave, ready, and start game."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.rooms.manager import (
    RoomManager,
    RoomState,
    PlayerSlot,
    ROLE_PRESETS,
)


# ── Unit tests for PlayerSlot / RoomState (no DB needed) ─────────


class TestPlayerSlot:
    def test_default_status_is_empty(self):
        slot = PlayerSlot(seat=1)
        assert slot.status == "empty"
        assert slot.agent_id is None

    def test_assigned_slot(self):
        slot = PlayerSlot(seat=1, agent_id="a1", agent_name="Bot1", status="occupied")
        assert slot.agent_id == "a1"
        assert slot.status == "occupied"


class TestRoomState:
    def test_creates_empty_slots(self):
        state = RoomState(room_id="r1", player_count=6)
        assert len(state.slots) == 6
        assert all(s.status == "empty" for s in state.slots)

    def test_occupied_count(self):
        state = RoomState(room_id="r1", player_count=6)
        state.slots[0].status = "occupied"
        state.slots[0].agent_id = "a1"
        assert state.occupied_count == 1
        assert not state.is_full

    def test_is_full(self):
        state = RoomState(room_id="r1", player_count=3)
        for i, s in enumerate(state.slots):
            s.agent_id = f"a{i}"
            s.status = "occupied"
        assert state.is_full

    def test_all_ready(self):
        state = RoomState(room_id="r1", player_count=2)
        state.slots[0].agent_id = "a1"
        state.slots[0].status = "ready"
        state.slots[1].agent_id = "a2"
        state.slots[1].status = "ready"
        assert state.all_ready

    def test_not_all_ready(self):
        state = RoomState(room_id="r1", player_count=2)
        state.slots[0].agent_id = "a1"
        state.slots[0].status = "ready"
        state.slots[1].agent_id = "a2"
        state.slots[1].status = "occupied"
        assert not state.all_ready

    def test_find_agent_slot(self):
        state = RoomState(room_id="r1", player_count=3)
        state.slots[1].agent_id = "target-agent"
        state.slots[1].status = "occupied"
        slot = state.find_agent_slot("target-agent")
        assert slot is not None
        assert slot.seat == 2

    def test_find_agent_slot_not_found(self):
        state = RoomState(room_id="r1", player_count=3)
        assert state.find_agent_slot("missing") is None

    def test_find_empty_slot(self):
        state = RoomState(room_id="r1", player_count=3)
        state.slots[0].status = "occupied"
        slot = state.find_empty_slot()
        assert slot is not None
        assert slot.seat == 2


# ── RoomManager unit tests with mocked DB ────────────────────────


class TestRoomManagerResolveRoles:
    def test_resolve_preset(self):
        manager = RoomManager()
        config = {"role_preset": "standard_9", "player_count": 9}
        roles = manager._resolve_roles(config)
        assert sum(roles.values()) == 9

    def test_resolve_custom_roles(self):
        manager = RoomManager()
        custom = {"werewolf": 2, "villager": 3, "seer": 1}
        config = {"custom_roles": custom, "player_count": 6}
        roles = manager._resolve_roles(config)
        assert roles == custom

    def test_custom_roles_mismatch_raises(self):
        manager = RoomManager()
        custom = {"werewolf": 2, "villager": 2}
        config = {"custom_roles": custom, "player_count": 6}
        with pytest.raises(ValueError, match="Custom roles total"):
            manager._resolve_roles(config)

    def test_preset_mismatch_raises(self):
        manager = RoomManager()
        config = {"role_preset": "standard_9", "player_count": 6}
        with pytest.raises(ValueError, match="requires 9 players"):
            manager._resolve_roles(config)

    def test_default_fallback(self):
        manager = RoomManager()
        config = {"player_count": 9}
        roles = manager._resolve_roles(config)
        assert sum(roles.values()) == 9

    def test_no_matching_preset_raises(self):
        manager = RoomManager()
        config = {"player_count": 7}
        with pytest.raises(ValueError, match="No default preset"):
            manager._resolve_roles(config)


class TestRolePresets:
    def test_presets_exist(self):
        assert len(ROLE_PRESETS) > 0

    def test_preset_counts_match(self):
        for name, preset in ROLE_PRESETS.items():
            total = sum(preset["roles"].values())
            assert total == preset["player_count"], f"Preset {name}: {total} != {preset['player_count']}"

    def test_standard_9_has_required_roles(self):
        preset = ROLE_PRESETS["standard_9"]
        assert "werewolf" in preset["roles"]
        assert "seer" in preset["roles"]
        assert "witch" in preset["roles"]
