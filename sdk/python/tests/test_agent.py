"""Tests for the WerewolfAgent base class — event handling and state management."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from werewolf_arena.agent import WerewolfAgent
from werewolf_arena.exceptions import ArenaConnectionError
from werewolf_arena.models import Action, GameEvent


class ConcreteAgent(WerewolfAgent):
    """A concrete test agent that tracks callback invocations."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.started = False
        self.ended = False
        self.night_action_called = False
        self.speech_called = False
        self.vote_called = False
        self.last_event: GameEvent | None = None

    async def on_game_start(self, event: GameEvent) -> None:
        self.started = True
        self.last_event = event

    async def on_night_action(self, event: GameEvent) -> Action | None:
        self.night_action_called = True
        self.last_event = event
        return Action(action_type="werewolf_kill", target=1)

    async def on_speech_turn(self, event: GameEvent) -> Action | None:
        self.speech_called = True
        self.last_event = event
        return Action(action_type="speech", content="test speech")

    async def on_vote(self, event: GameEvent) -> Action | None:
        self.vote_called = True
        self.last_event = event
        return Action(action_type="vote", target=3)

    async def on_game_end(self, event: GameEvent) -> None:
        self.ended = True
        self.last_event = event


class TestAgentInit:
    """Test agent initialization."""

    def test_init_basic(self):
        agent = ConcreteAgent(
            api_key="test-key",
            server_url="http://localhost:8000",
        )
        assert agent.api_key == "test-key"
        assert agent.server_url == "http://localhost:8000"
        assert agent.agent_name == "Agent"
        assert agent.game_id is None
        assert agent.room_id is None
        assert agent.seat is None
        assert agent.role is None
        assert agent.is_connected is False

    def test_init_with_name(self):
        agent = ConcreteAgent(
            api_key="test-key",
            server_url="http://localhost:8000/",
            agent_name="TestBot",
        )
        assert agent.agent_name == "TestBot"
        assert agent.server_url == "http://localhost:8000"  # trailing slash stripped

    def test_set_game_id(self):
        agent = ConcreteAgent(api_key="k", server_url="http://localhost:8000")
        assert agent.game_id is None
        agent.set_game_id("game-123")
        assert agent.game_id == "game-123"


class TestAgentStateSync:
    """Test internal state updates from game.sync events."""

    def test_update_state_from_sync(self):
        agent = ConcreteAgent(api_key="k", server_url="http://localhost:8000")
        data = {
            "game_id": "g-1",
            "status": "in_progress",
            "current_phase": "night_werewolf",
            "current_round": 2,
            "your_seat": 3,
            "your_role": "seer",
            "players": [
                {"seat": 1, "is_alive": True},
                {"seat": 2, "is_alive": False},
            ],
        }
        agent._update_state_from_sync(data)

        assert agent.game_id == "g-1"
        assert agent.role == "seer"
        assert agent.seat == 3
        assert agent.game_state is not None
        assert agent.game_state.status == "in_progress"
        assert agent.game_state.current_round == 2


class TestAgentEventCreation:
    """Test internal event creation."""

    def test_make_event(self):
        agent = ConcreteAgent(api_key="k", server_url="http://localhost:8000")
        agent.set_game_id("game-1")

        event = agent._make_event("test.event", {"key": "value"})
        assert event.event_type == "test.event"
        assert event.game_id == "game-1"
        assert event.data["key"] == "value"


class TestAgentConnect:
    """Test connection logic."""

    @pytest.mark.asyncio
    async def test_connect_without_game_id_raises(self):
        agent = ConcreteAgent(api_key="k", server_url="http://localhost:8000")
        with pytest.raises(ArenaConnectionError, match="No game_id"):
            await agent.connect()


class TestAgentActionSubmission:
    """Test action convenience methods."""

    def test_send_speech_action(self):
        """Verify send_speech creates the right Action."""
        # We can't test full submit without a server, but we can test
        # that the action would be correct
        action = Action(action_type="speech", content="Hello!")
        body = action.to_request_body()
        assert body["action_type"] == "speech"
        assert body["content"] == "Hello!"

    def test_vote_action(self):
        action = Action(action_type="vote", target=5)
        body = action.to_request_body()
        assert body["action_type"] == "vote"
        assert body["target_seat"] == 5

    def test_abstain_action(self):
        action = Action(action_type="vote_abstain")
        body = action.to_request_body()
        assert body["action_type"] == "vote_abstain"
        assert "target_seat" not in body
