"""Tests for game statistics generation."""

from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.action import GameAction
from app.models.agent import Agent
from app.models.event import GameEvent
from app.models.game import Game
from app.models.player import GamePlayer
from app.models.room import Room
from app.models.user import User
from app.security.auth import hash_api_key, hash_password
from app.spectator.stats import get_game_stats


@pytest_asyncio.fixture
async def game_with_stats(client) -> str:
    """Create a game with vote/speech actions for stats testing.

    Returns game_id.
    """
    from tests.conftest import test_session_factory

    async with test_session_factory() as db:
        user = User(
            id=str(uuid4()),
            username=f"stats_user_{uuid4().hex[:6]}",
            email=f"stats_{uuid4().hex[:6]}@test.com",
            password_hash=hash_password("test"),
        )
        db.add(user)
        await db.flush()

        agents = []
        for i in range(6):
            agent = Agent(
                id=str(uuid4()),
                name=f"StatsAgent{i}",
                api_key_hash=hash_api_key(f"stats-key-{i}-{uuid4().hex}"),
                owner_id=user.id,
            )
            db.add(agent)
            agents.append(agent)
        await db.flush()

        room = Room(
            id=str(uuid4()),
            name="Stats Test Room",
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
            current_round=2,
            role_config={"werewolf": 2, "villager": 2, "seer": 1, "witch": 1},
            winner="werewolf",
        )
        db.add(game)
        await db.flush()

        roles = ["werewolf", "villager", "seer", "werewolf", "witch", "villager"]
        players = []
        for i, agent in enumerate(agents):
            player = GamePlayer(
                id=str(uuid4()),
                game_id=game.id,
                agent_id=agent.id,
                seat=i + 1,
                role=roles[i],
                is_alive=i < 4,
                death_round=1 if i >= 4 else None,
                death_cause="killed" if i >= 4 else None,
            )
            db.add(player)
            players.append(player)
        await db.flush()

        # Add vote actions
        vote_actions = [
            (players[0], 1, 3, "vote"),   # seat 1 votes seat 3
            (players[1], 1, 1, "vote"),   # seat 2 votes seat 1
            (players[2], 1, 1, "vote"),   # seat 3 votes seat 1
            (players[3], 1, 3, "vote"),   # seat 4 votes seat 3
            (players[4], 1, 1, "vote"),   # seat 5 votes seat 1
            (players[0], 2, 2, "vote"),   # round 2: seat 1 votes seat 2
            (players[1], 2, 4, "vote"),   # round 2: seat 2 votes seat 4
        ]
        for player, rnd, target, atype in vote_actions:
            action = GameAction(
                id=str(uuid4()),
                game_id=game.id,
                player_id=player.id,
                action_type=atype,
                round=rnd,
                phase="day_vote",
                target_seat=target,
            )
            db.add(action)

        # Add speech actions
        speech_actions = [
            (players[0], 1, "I am a villager, trust me!"),
            (players[1], 1, "I think seat 1 is suspicious."),
            (players[2], 1, "I checked seat 1, they are werewolf!"),
            (players[0], 2, "The seer is lying!"),
        ]
        for player, rnd, content in speech_actions:
            action = GameAction(
                id=str(uuid4()),
                game_id=game.id,
                player_id=player.id,
                action_type="speech",
                round=rnd,
                phase="day_speech",
                content=content,
            )
            db.add(action)

        await db.commit()
        return game.id


class TestGameStats:
    """Tests for game statistics."""

    @pytest.mark.asyncio
    async def test_get_stats_success(self, game_with_stats: str):
        """Stats should contain vote flow, heatmap, speech stats, timeline."""
        from tests.conftest import test_session_factory

        async with test_session_factory() as db:
            stats = await get_game_stats(db, game_with_stats)

        assert stats is not None
        assert stats["game_id"] == game_with_stats
        assert stats["winner"] == "werewolf"

        # Vote flow
        assert "vote_flow" in stats
        assert len(stats["vote_flow"]) >= 1
        round1_votes = next(
            (r for r in stats["vote_flow"] if r["round"] == 1), None
        )
        assert round1_votes is not None
        assert len(round1_votes["votes"]) == 5  # 5 votes in round 1

        # Identity heatmap
        assert "identity_heatmap" in stats
        assert stats["identity_heatmap"]["total_votes"] > 0
        matrix = stats["identity_heatmap"]["matrix"]
        assert len(matrix) > 0
        for entry in matrix:
            assert "voter_seat" in entry
            assert "target_seat" in entry
            assert "count" in entry

        # Speech stats
        assert "speech_stats" in stats
        assert len(stats["speech_stats"]) >= 1
        seat1_speech = next(
            (s for s in stats["speech_stats"] if s["seat"] == 1), None
        )
        assert seat1_speech is not None
        assert seat1_speech["speech_count"] == 2
        assert seat1_speech["average_length"] > 0

        # Survival timeline
        assert "survival_timeline" in stats
        assert len(stats["survival_timeline"]) >= 1

        # Player roles
        assert "player_roles" in stats
        assert stats["player_roles"]["1"] == "werewolf"

    @pytest.mark.asyncio
    async def test_get_stats_not_found(self):
        """Stats for non-existent game should return None."""
        from tests.conftest import test_session_factory

        async with test_session_factory() as db:
            stats = await get_game_stats(db, "non-existent-game-id")

        assert stats is None
