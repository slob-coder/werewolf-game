"""Tests for the role system."""

import pytest

from app.engine.state_machine import GamePhase
from app.roles import (
    RoleRegistry,
    Werewolf,
    Seer,
    Witch,
    Hunter,
    Guard,
    Idiot,
    Villager,
    Faction,
    ActionType,
)


class TestRoleRegistry:
    def test_all_roles_registered(self):
        names = RoleRegistry.all_names()
        assert "werewolf" in names
        assert "seer" in names
        assert "witch" in names
        assert "hunter" in names
        assert "guard" in names
        assert "idiot" in names
        assert "villager" in names
        assert len(names) >= 7

    def test_get_known_role(self):
        cls = RoleRegistry.get("werewolf")
        assert cls is Werewolf

    def test_get_unknown_role(self):
        with pytest.raises(KeyError, match="Unknown role"):
            RoleRegistry.get("vampire")

    def test_create_instance(self):
        role = RoleRegistry.create("seer")
        assert isinstance(role, Seer)

    def test_create_from_config(self):
        config = {"werewolf": 3, "seer": 1, "villager": 2}
        roles = RoleRegistry.create_from_config(config)
        assert len(roles) == 6
        assert sum(1 for r in roles if isinstance(r, Werewolf)) == 3
        assert sum(1 for r in roles if isinstance(r, Seer)) == 1
        assert sum(1 for r in roles if isinstance(r, Villager)) == 2


class TestWerewolf:
    def test_attributes(self):
        w = Werewolf()
        assert w.name == "werewolf"
        assert w.faction == Faction.WEREWOLF
        assert w.has_night_action is True
        assert w.priority == 10

    def test_can_act(self):
        w = Werewolf()
        assert w.can_act(GamePhase.NIGHT_WEREWOLF) is True
        assert w.can_act(GamePhase.DAY_VOTE) is False
        assert w.can_act(GamePhase.NIGHT_WEREWOLF, is_alive=False) is False

    def test_action_types(self):
        w = Werewolf()
        types = w.get_action_types()
        assert ActionType.WEREWOLF_KILL in types
        assert ActionType.WEREWOLF_CHAT in types


class TestSeer:
    def test_attributes(self):
        s = Seer()
        assert s.faction == Faction.GOD
        assert s.has_night_action is True
        assert s.action_phase == GamePhase.NIGHT_SEER

    def test_can_act(self):
        s = Seer()
        assert s.can_act(GamePhase.NIGHT_SEER) is True
        assert s.can_act(GamePhase.NIGHT_WEREWOLF) is False

    def test_action_types(self):
        assert ActionType.SEER_CHECK in Seer().get_action_types()


class TestWitch:
    def test_initial_potions(self):
        w = Witch()
        assert w.has_save_potion is True
        assert w.has_poison_potion is True

    def test_use_save(self):
        w = Witch()
        assert w.use_save() is True
        assert w.has_save_potion is False
        assert w.use_save() is False

    def test_use_poison(self):
        w = Witch()
        assert w.use_poison() is True
        assert w.has_poison_potion is False
        assert w.use_poison() is False

    def test_action_types_all_available(self):
        w = Witch()
        types = w.get_action_types()
        assert ActionType.WITCH_SAVE in types
        assert ActionType.WITCH_POISON in types
        assert ActionType.WITCH_SKIP in types

    def test_action_types_after_using_potions(self):
        w = Witch()
        w.use_save()
        w.use_poison()
        types = w.get_action_types()
        assert ActionType.WITCH_SAVE not in types
        assert ActionType.WITCH_POISON not in types
        assert ActionType.WITCH_SKIP in types


class TestHunter:
    def test_attributes(self):
        h = Hunter()
        assert h.faction == Faction.GOD
        assert h.has_night_action is False

    def test_can_act_in_hunter_phases(self):
        h = Hunter()
        assert h.can_act(GamePhase.HUNTER_SHOOT) is True
        assert h.can_act(GamePhase.NIGHT_HUNTER) is True
        assert h.can_act(GamePhase.DAY_VOTE) is False

    def test_on_death_normal_can_shoot(self):
        h = Hunter()
        result = h.on_death("werewolf_kill")
        assert result is not None
        assert result["hunter_can_shoot"] is True

    def test_on_death_poison_cannot_shoot(self):
        h = Hunter()
        result = h.on_death("poison")
        assert result is not None
        assert result["hunter_can_shoot"] is False


class TestGuard:
    def test_attributes(self):
        g = Guard()
        assert g.faction == Faction.GOD
        assert g.has_night_action is True
        assert g.priority == 5

    def test_protect_first_night(self):
        g = Guard()
        assert g.protect(3) is True
        assert g.last_protected_seat == 3

    def test_cannot_protect_same_twice(self):
        g = Guard()
        g.protect(3)
        assert g.protect(3) is False

    def test_can_protect_different(self):
        g = Guard()
        g.protect(3)
        assert g.protect(5) is True
        assert g.last_protected_seat == 5


class TestIdiot:
    def test_initial_state(self):
        i = Idiot()
        assert i.has_revealed is False
        assert i.can_vote is True

    def test_first_vote_survives(self):
        i = Idiot()
        assert i.on_vote_execution() is True
        assert i.has_revealed is True
        assert i.can_vote is False

    def test_second_vote_dies(self):
        i = Idiot()
        i.on_vote_execution()  # survives first
        assert i.on_vote_execution() is False

    def test_no_active_ability(self):
        i = Idiot()
        assert i.can_act(GamePhase.NIGHT_WEREWOLF) is False
        assert i.get_action_types() == []


class TestVillager:
    def test_attributes(self):
        v = Villager()
        assert v.faction == Faction.VILLAGER
        assert v.has_night_action is False
        assert v.can_act(GamePhase.NIGHT_WEREWOLF) is False
        assert v.get_action_types() == []
