"""Tests for the spectator and stats API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.models.action import GameAction
from app.models.agent import Agent
from app.models.event import GameEvent
from app.models.game import Game
from app.models.player import GamePlayer
from app.models.room import Room
from app.models.user import User
from app.security.auth import hash_api_key, hash_password


@pytest_asyncio.fixture
async def seeded_game(client: AsyncClient) -> str:
    """Create a minimal game with events/actions for API testing. Returns game_id."""
    from tests.conftest import test_session_factory

    async with test_session_factory() as db:
        user = User(
            id=str(uuid4()),
            username=f"api_user_{uuid4().hex[:6]}",
            email=f"api_{uuid4().hex[:6]}@test.com",
            password_hash=hash_password("pass"),
        )
        db.add(user)
        await db.flush()

        agent = Agent(
            id=str(uuid4()),
            name="APIAgent",
            api_key_hash=hash_api_key(f"api-key-{uuid4().hex}"),
            owner_id=user.id,
        )
        db.add(agent)
        await db.flush()

        room = Room(
            id=str(uuid4()),
            name="API Test Room",
            config={"player_count": 6},
            status="in_progress",
            created_by=user.id,
        )
        db.add(room)
        await db.flush()

        game = Game(
            id=str(uuid4()),
            room_id=room.id,
            status="finished",
            current_phase="game_over",
            current_round=1,
            role_config={"werewolf": 2, "villager": 2, "seer": 1, "witch": 1},
            winner="villager",
        )
        db.add(game)
        await db.flush()

        player = GamePlayer(
            id=str(uuid4()),
            game_id=game.id,
            agent_id=agent.id,
            seat=1,
            role="werewolf",
        )
        db.add(player)
        await db.flush()

        event = GameEvent(
            id=str(uuid4()),
            game_id=game.id,
            event_type="game.start",
            round=1,
            phase="role_assignment",
            data={},
            visibility="public",
        )
        db.add(event)

        action = GameAction(
            id=str(uuid4()),
            game_id=game.id,
            player_id=player.id,
            action_type="speech",
            round=1,
            phase="day_speech",
            content="Hello world",
        )
        db.add(action)

        await db.commit()
        return game.id


class TestReplayAPI:
    """Tests for GET /api/v1/games/{game_id}/replay."""

    @pytest.mark.asyncio
    async def test_replay_success(self, client: AsyncClient, seeded_game: str):
        """Valid game_id should return replay data."""
        resp = await client.get(f"/api/v1/games/{seeded_game}/replay")
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_id"] == seeded_game
        assert "events" in data
        assert "players" in data
        assert "actions" in data

    @pytest.mark.asyncio
    async def test_replay_not_found(self, client: AsyncClient):
        """Non-existent game should return 404."""
        resp = await client.get("/api/v1/games/non-existent-id/replay")
        assert resp.status_code == 404


class TestStatsAPI:
    """Tests for GET /api/v1/games/{game_id}/stats."""

    @pytest.mark.asyncio
    async def test_stats_success(self, client: AsyncClient, seeded_game: str):
        """Valid game_id should return stats data."""
        resp = await client.get(f"/api/v1/games/{seeded_game}/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_id"] == seeded_game
        assert "vote_flow" in data
        assert "identity_heatmap" in data
        assert "speech_stats" in data
        assert "survival_timeline" in data
        assert "player_roles" in data

    @pytest.mark.asyncio
    async def test_stats_not_found(self, client: AsyncClient):
        """Non-existent game should return 404."""
        resp = await client.get("/api/v1/games/non-existent-id/stats")
        assert resp.status_code == 404
