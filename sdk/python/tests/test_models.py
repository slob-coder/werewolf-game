"""Tests for the Werewolf Arena Python SDK — models and data types."""

from werewolf_arena.models import (
    Action,
    ActionType,
    GameEvent,
    GamePhase,
    GameState,
    PhaseInfo,
    PlayerInfo,
    RoleConfig,
    RoomInfo,
)


class TestAction:
    """Tests for the Action model."""

    def test_action_with_target(self):
        action = Action(action_type="werewolf_kill", target=3)
        assert action.action_type == "werewolf_kill"
        assert action.target == 3
        assert action.content is None

    def test_action_with_content(self):
        action = Action(action_type="speech", content="Hello world")
        assert action.action_type == "speech"
        assert action.content == "Hello world"
        assert action.target is None

    def test_action_to_request_body_with_target(self):
        action = Action(action_type="vote", target=5)
        body = action.to_request_body()
        assert body == {"action_type": "vote", "target_seat": 5}

    def test_action_to_request_body_with_content(self):
        action = Action(action_type="speech", content="I'm a villager")
        body = action.to_request_body()
        assert body == {"action_type": "speech", "content": "I'm a villager"}

    def test_action_to_request_body_with_metadata(self):
        action = Action(
            action_type="speech",
            content="test",
            metadata={"chain_of_thought": "reasoning..."},
        )
        body = action.to_request_body()
        assert "metadata" in body
        assert body["metadata"]["chain_of_thought"] == "reasoning..."

    def test_action_to_request_body_minimal(self):
        action = Action(action_type="witch_skip")
        body = action.to_request_body()
        assert body == {"action_type": "witch_skip"}


class TestGameEvent:
    """Tests for the GameEvent model."""

    def test_basic_event(self):
        event = GameEvent(
            event_type="game.start",
            game_id="game-123",
            data={"your_role": "seer", "your_seat": 3},
        )
        assert event.event_type == "game.start"
        assert event.game_id == "game-123"
        assert event.data["your_role"] == "seer"

    def test_event_defaults(self):
        event = GameEvent(event_type="test")
        assert event.game_id == ""
        assert event.round == 0
        assert event.phase == ""
        assert event.data == {}
        assert event.visibility == "public"


class TestGameState:
    """Tests for the GameState model."""

    def test_full_state(self):
        state = GameState(
            game_id="g-1",
            room_id="r-1",
            status="in_progress",
            current_phase="night_werewolf",
            current_round=2,
            my_seat=3,
            my_role="werewolf",
            players=[
                PlayerInfo(seat=1, is_alive=True),
                PlayerInfo(seat=2, is_alive=False),
                PlayerInfo(seat=3, is_alive=True, role="werewolf"),
            ],
        )
        assert state.game_id == "g-1"
        assert state.current_round == 2
        assert len(state.players) == 3
        assert state.players[2].role == "werewolf"

    def test_state_defaults(self):
        state = GameState(game_id="test", status="waiting")
        assert state.room_id == ""
        assert state.current_round == 0
        assert state.players == []
        assert state.winner is None


class TestPlayerInfo:
    def test_player_defaults(self):
        player = PlayerInfo(seat=1)
        assert player.seat == 1
        assert player.is_alive is True
        assert player.role is None
        assert player.agent_name is None

    def test_player_full(self):
        player = PlayerInfo(seat=5, agent_name="Bot5", is_alive=False, role="seer")
        assert player.seat == 5
        assert player.agent_name == "Bot5"
        assert player.is_alive is False
        assert player.role == "seer"


class TestPhaseInfo:
    def test_phase_info(self):
        phase = PhaseInfo(phase=GamePhase.NIGHT_WEREWOLF, round=1, timeout_seconds=60)
        assert phase.phase == GamePhase.NIGHT_WEREWOLF
        assert phase.round == 1


class TestEnums:
    def test_game_phases(self):
        assert GamePhase.WAITING.value == "waiting"
        assert GamePhase.NIGHT_WEREWOLF.value == "night_werewolf"
        assert GamePhase.DAY_VOTE.value == "day_vote"
        assert GamePhase.GAME_OVER.value == "game_over"

    def test_action_types(self):
        assert ActionType.WEREWOLF_KILL.value == "werewolf_kill"
        assert ActionType.SEER_CHECK.value == "seer_check"
        assert ActionType.SPEECH.value == "speech"
        assert ActionType.VOTE.value == "vote"


class TestRoomInfo:
    def test_room_info(self):
        room = RoomInfo(
            id="room-1",
            name="Test Room",
            status="open",
            player_count=9,
            current_players=3,
        )
        assert room.id == "room-1"
        assert room.name == "Test Room"
        assert room.player_count == 9


class TestRoleConfig:
    def test_role_config(self):
        config = RoleConfig(werewolf=3, seer=1, witch=1, hunter=1, villager=3)
        assert config.werewolf == 3
        assert config.seer == 1
        assert config.villager == 3
