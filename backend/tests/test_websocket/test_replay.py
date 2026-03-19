"""Tests for replay data generation."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action import GameAction
from app.models.event import GameEvent
from app.models.game import Game
from app.models.player import GamePlayer
from app.spectator.replay import get_replay_data


@pytest_asyncio.fixture
async def game_with_events(client) -> tuple[str, str]:
    """Create a game with events and actions for replay testing.

    Returns (game_id, room_id).
    """
    from app.models.agent import Agent
    from app.models.room import Room
    from app.models.user import User
    from app.security.auth import hash_api_key, hash_password

    from tests.conftest import test_session_factory

    async with test_session_factory() as db:
        # Create user
        user = User(
            id=str(uuid4()),
            username=f"replay_user_{uuid4().hex[:6]}",
            email=f"replay_{uuid4().hex[:6]}@test.com",
            password_hash=hash_password("test"),
        )
        db.add(user)
        await db.flush()

        # Create agents
        agents = []
        for i in range(6):
            agent = Agent(
                id=str(uuid4()),
                name=f"ReplayAgent{i}",
                api_key_hash=hash_api_key(f"replay-key-{i}-{uuid4().hex}"),
                owner_id=user.id,
            )
            db.add(agent)
            agents.append(agent)
        await db.flush()

        # Create room
        room = Room(
            id=str(uuid4()),
            name="Replay Test Room",
            config={"player_count": 6, "role_preset": "simple_6"},
            status="in_progress",
            created_by=user.id,
        )
        db.add(room)
        await db.flush()

        # Create game
        game = Game(
            id=str(uuid4()),
            room_id=room.id,
            status="finished",
            current_phase="game_over",
            current_round=3,
            role_config={"werewolf": 2, "villager": 2, "seer": 1, "witch": 1},
            winner="villager",
            win_reason="All werewolves eliminated",
        )
        db.add(game)
        await db.flush()

        # Create players
        roles = ["werewolf", "villager", "seer", "werewolf", "witch", "villager"]
        for i, agent in enumerate(agents):
            player = GamePlayer(
                id=str(uuid4()),
                game_id=game.id,
                agent_id=agent.id,
                seat=i + 1,
                role=roles[i],
                is_alive=i > 0,  # seat 1 (werewolf) is dead
                death_round=2 if i == 0 else None,
                death_cause="voted" if i == 0 else None,
            )
            db.add(player)
        await db.flush()

        # Create events
        events_data = [
            ("game.start", 1, "role_assignment", "public", {}),
            ("phase.change", 1, "night_werewolf", "public", {"phase": "night_werewolf"}),
            ("phase.change", 1, "day_speech", "public", {"phase": "day_speech"}),
            ("vote.result", 1, "day_vote_result", "public", {"eliminated_seat": 1}),
            ("phase.change", 2, "night_werewolf", "public", {"phase": "night_werewolf"}),
            ("game.end", 3, "game_over", "public", {"winner": "villager"}),
        ]
        for event_type, round_num, phase, vis, data in events_data:
            event = GameEvent(
                id=str(uuid4()),
                game_id=game.id,
                event_type=event_type,
                round=round_num,
                phase=phase,
                data=data,
                visibility=vis,
            )
            db.add(event)

        # Create actions
        player_result = await db.execute(
            __import__("sqlalchemy").select(GamePlayer).where(
                GamePlayer.game_id == game.id
            )
        )
        players = player_result.scalars().all()
        player_map = {p.seat: p for p in players}

        action = GameAction(
            id=str(uuid4()),
            game_id=game.id,
            player_id=player_map[2].id,
            action_type="vote",
            round=1,
            phase="day_vote",
            target_seat=1,
        )
        db.add(action)

        await db.commit()
        return game.id, room.id


class TestReplayData:
    """Tests for replay data generation."""

    @pytest.mark.asyncio
    async def test_get_replay_data_success(self, game_with_events):
        """Replay data should contain all game information."""
        from tests.conftest import test_session_factory

        game_id, _ = game_with_events

        async with test_session_factory() as db:
            replay = await get_replay_data(db, game_id)

        assert replay is not None
        assert replay["game_id"] == game_id
        assert replay["status"] == "finished"
        assert replay["winner"] == "villager"
        assert replay["total_rounds"] == 3
        assert len(replay["players"]) == 6
        assert len(replay["events"]) >= 6
        assert len(replay["actions"]) >= 1

        # Players should have full god-view data
        p1 = next(p for p in replay["players"] if p["seat"] == 1)
        assert p1["role"] == "werewolf"
        assert p1["death_round"] == 2

        # Events should have timestamps
        for ev in replay["events"]:
            assert "timestamp" in ev
            assert "event_type" in ev
            assert "phase" in ev

    @pytest.mark.asyncio
    async def test_get_replay_data_not_found(self):
        """Replay for non-existent game should return None."""
        from tests.conftest import test_session_factory

        async with test_session_factory() as db:
            replay = await get_replay_data(db, "non-existent-game-id")

        assert replay is None
