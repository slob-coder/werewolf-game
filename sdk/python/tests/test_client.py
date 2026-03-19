"""Tests for the ArenaRESTClient."""

from __future__ import annotations

import pytest

from werewolf_arena.client import ArenaRESTClient
from werewolf_arena.models import Action


class TestClientInit:
    """Test REST client initialization."""

    def test_init(self):
        client = ArenaRESTClient("http://localhost:8000", "test-key")
        assert client.server_url == "http://localhost:8000"
        assert client.api_key == "test-key"
        assert client._base_url == "http://localhost:8000/api/v1"

    def test_init_strips_trailing_slash(self):
        client = ArenaRESTClient("http://localhost:8000/", "test-key")
        assert client.server_url == "http://localhost:8000"
        assert client._base_url == "http://localhost:8000/api/v1"


class TestActionSerialization:
    """Test Action → request body serialization used by the client."""

    def test_action_with_all_fields(self):
        action = Action(
            action_type="werewolf_kill",
            target=5,
            content="test",
            metadata={"foo": "bar"},
        )
        body = action.to_request_body()
        assert body == {
            "action_type": "werewolf_kill",
            "target_seat": 5,
            "content": "test",
            "metadata": {"foo": "bar"},
        }

    def test_action_minimal(self):
        action = Action(action_type="witch_skip")
        body = action.to_request_body()
        assert body == {"action_type": "witch_skip"}
