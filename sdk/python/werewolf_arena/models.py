"""Pydantic data models for the Werewolf Arena SDK."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional, List, Dict

from pydantic import BaseModel, Field


class GamePhase(str, Enum):
    WAITING = "waiting"
    ROLE_ASSIGNMENT = "role_assignment"
    NIGHT_START = "night_start"
    NIGHT_WEREWOLF = "night_werewolf"
    NIGHT_SEER = "night_seer"
    NIGHT_WITCH = "night_witch"
    NIGHT_HUNTER = "night_hunter"
    NIGHT_GUARD = "night_guard"
    NIGHT_END = "night_end"
    DAY_ANNOUNCEMENT = "day_announcement"
    DAY_SPEECH = "day_speech"
    DAY_VOTE = "day_vote"
    DAY_VOTE_RESULT = "day_vote_result"
    HUNTER_SHOOT = "hunter_shoot"
    LAST_WORDS = "last_words"
    GAME_OVER = "game_over"


class Faction(str, Enum):
    WEREWOLF = "werewolf"
    VILLAGER = "villager"
    GOD = "god"


class ActionType(str, Enum):
    WEREWOLF_KILL = "werewolf_kill"
    WEREWOLF_CHAT = "werewolf_chat"
    SEER_CHECK = "seer_check"
    WITCH_SAVE = "witch_save"
    WITCH_POISON = "witch_poison"
    WITCH_SKIP = "witch_skip"
    GUARD_PROTECT = "guard_protect"
    HUNTER_SHOOT = "hunter_shoot"
    HUNTER_SKIP = "hunter_skip"
    SPEECH = "speech"
    VOTE = "vote"
    VOTE_ABSTAIN = "vote_abstain"
    LAST_WORDS = "last_words"


class RoomStatus(str, Enum):
    WAITING = "waiting"
    READY = "ready"
    PLAYING = "playing"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class PlayerInfo(BaseModel):
    seat: int
    agent_name: Optional[str] = None
    is_alive: bool = True
    role: Optional[str] = None


class PhaseInfo(BaseModel):
    phase: GamePhase
    round: int
    timeout_seconds: Optional[int] = None


class RoleConfig(BaseModel):
    werewolf: int = 0
    seer: int = 0
    witch: int = 0
    hunter: int = 0
    guard: int = 0
    idiot: int = 0
    villager: int = 0


class GameState(BaseModel):
    game_id: str
    room_id: str = ""
    status: str
    current_phase: Optional[str] = None
    current_round: int = 0
    my_seat: Optional[int] = None
    my_role: Optional[str] = None
    players: List[PlayerInfo] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    winner: Optional[str] = None


class GameEvent(BaseModel):
    event_type: str
    game_id: str = ""
    timestamp: Optional[str] = None
    round: int = 0
    phase: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    visibility: str = "public"


class Action(BaseModel):
    action_type: str
    target: Optional[int] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_request_body(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {"action_type": self.action_type}
        if self.target is not None:
            body["target_seat"] = self.target
        if self.content is not None:
            body["content"] = self.content
        if self.metadata is not None:
            body["metadata"] = self.metadata
        return body


class RoomInfo(BaseModel):
    id: str
    name: str
    status: str
    player_count: int = 0
    current_players: int = 0
    current_game_id: Optional[str] = None  # 当前关联的游戏 ID（进行中的游戏）
    config: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class SlotInfo(BaseModel):
    seat: int
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    status: str = "empty"


class SpeechRecord(BaseModel):
    seat: int
    content: str
    agent_name: Optional[str] = None
    timestamp: Optional[str] = None


class VoteRecord(BaseModel):
    voter_seat: int
    target_seat: Optional[int] = None
    timestamp: Optional[str] = None


class DeathRecord(BaseModel):
    seat: int
    cause: str
    round: int
