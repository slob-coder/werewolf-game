"""Room manager — CRUD, lifecycle, and PlayerSlot management."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.game import Game
from app.models.player import GamePlayer
from app.models.room import Room

logger = logging.getLogger(__name__)

# ── Role presets ─────────────────────────────────────────────────

ROLE_PRESETS: dict[str, dict[str, Any]] = {
    "standard_9": {
        "display_name": "标准9人局",
        "player_count": 9,
        "roles": {
            "werewolf": 3,
            "villager": 3,
            "seer": 1,
            "witch": 1,
            "hunter": 1,
        },
        "description": "经典9人配置：3狼3民 + 预言家、女巫、猎人",
    },
    "standard_12": {
        "display_name": "标准12人局",
        "player_count": 12,
        "roles": {
            "werewolf": 4,
            "villager": 4,
            "seer": 1,
            "witch": 1,
            "hunter": 1,
            "guard": 1,
        },
        "description": "12人配置：4狼4民 + 预言家、女巫、猎人、守卫",
    },
    "guard_9": {
        "display_name": "守卫9人局",
        "player_count": 9,
        "roles": {
            "werewolf": 3,
            "villager": 2,
            "seer": 1,
            "witch": 1,
            "hunter": 1,
            "guard": 1,
        },
        "description": "9人守卫局：3狼2民 + 预言家、女巫、猎人、守卫",
    },
    "idiot_9": {
        "display_name": "白痴9人局",
        "player_count": 9,
        "roles": {
            "werewolf": 3,
            "villager": 2,
            "seer": 1,
            "witch": 1,
            "hunter": 1,
            "idiot": 1,
        },
        "description": "9人白痴局：3狼2民 + 预言家、女巫、猎人、白痴",
    },
    "simple_6": {
        "display_name": "简易6人局",
        "player_count": 6,
        "roles": {
            "werewolf": 2,
            "villager": 2,
            "seer": 1,
            "witch": 1,
        },
        "description": "6人简易局：2狼2民 + 预言家、女巫",
    },
}


# ── PlayerSlot data class ────────────────────────────────────────


@dataclass
class PlayerSlot:
    """In-memory representation of a seat in a room."""

    seat: int
    agent_id: str | None = None
    agent_name: str | None = None
    status: Literal["empty", "occupied", "ready", "disconnected"] = "empty"
    connected_at: datetime | None = None


# ── RoomState — in-memory state for an active room ───────────────


@dataclass
class RoomState:
    """In-memory state for a room, including player slots."""

    room_id: str
    player_count: int
    slots: list[PlayerSlot] = field(default_factory=list)
    game_id: str | None = None

    def __post_init__(self) -> None:
        if not self.slots:
            self.slots = [
                PlayerSlot(seat=i + 1) for i in range(self.player_count)
            ]

    @property
    def occupied_count(self) -> int:
        return sum(1 for s in self.slots if s.status != "empty")

    @property
    def is_full(self) -> bool:
        return self.occupied_count >= self.player_count

    @property
    def all_ready(self) -> bool:
        return all(
            s.status == "ready"
            for s in self.slots
            if s.status != "empty"
        ) and self.occupied_count > 0

    def find_agent_slot(self, agent_id: str) -> PlayerSlot | None:
        for s in self.slots:
            if s.agent_id == agent_id:
                return s
        return None

    def find_empty_slot(self) -> PlayerSlot | None:
        for s in self.slots:
            if s.status == "empty":
                return s
        return None


# ── RoomManager ──────────────────────────────────────────────────


class RoomManager:
    """Manages room lifecycle, player slots, and game creation.

    Maintains in-memory RoomState for active rooms, backed by DB for
    persistence.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, RoomState] = {}

    # ── helpers ───────────────────────────────────────────────

    def _get_state(self, room_id: str) -> RoomState | None:
        return self._rooms.get(room_id)

    def _ensure_state(self, room: Room) -> RoomState:
        """Return existing in-memory state or create from DB record."""
        if room.id not in self._rooms:
            pc = room.config.get("player_count", 9) if room.config else 9
            self._rooms[room.id] = RoomState(room_id=room.id, player_count=pc)
        return self._rooms[room.id]

    def _resolve_roles(self, config: dict) -> dict[str, int]:
        """Resolve role configuration from preset or custom roles."""
        preset_name = config.get("role_preset")
        custom = config.get("custom_roles")
        player_count = config.get("player_count", 9)

        if custom:
            total = sum(custom.values())
            if total != player_count:
                raise ValueError(
                    f"Custom roles total ({total}) != player_count ({player_count})"
                )
            return custom

        if preset_name and preset_name in ROLE_PRESETS:
            preset = ROLE_PRESETS[preset_name]
            if preset["player_count"] != player_count:
                raise ValueError(
                    f"Preset '{preset_name}' requires {preset['player_count']} players, "
                    f"but room has {player_count}"
                )
            return preset["roles"]

        # Default: find a matching preset by player count
        for preset in ROLE_PRESETS.values():
            if preset["player_count"] == player_count:
                return preset["roles"]

        raise ValueError(f"No default preset for {player_count} players")

    # ── CRUD ─────────────────────────────────────────────────

    async def create_room(
        self,
        db: AsyncSession,
        request: Any,
        created_by: str | None = None,
    ) -> Room:
        """Create a new room with the given configuration."""
        config = {
            "player_count": request.player_count,
            "role_preset": request.role_preset,
            "custom_roles": request.custom_roles,
            "speech_timeout": request.speech_timeout,
            "action_timeout": request.action_timeout,
            "vote_timeout": request.vote_timeout,
            "allow_spectators": request.allow_spectators,
            "max_spectators": request.max_spectators,
            "auto_start": request.auto_start,
            "content_filter": request.content_filter,
        }

        room = Room(
            name=request.name,
            config=config,
            status="waiting",
            created_by=created_by,
        )
        db.add(room)
        await db.flush()
        await db.refresh(room)

        # Initialize in-memory state
        self._ensure_state(room)
        logger.info("Room created: %s (%s)", room.id, room.name)
        return room

    async def get_room(self, db: AsyncSession, room_id: str) -> Room | None:
        """Fetch a room by ID."""
        result = await db.execute(select(Room).where(Room.id == room_id))
        return result.scalar_one_or_none()

    async def list_rooms(
        self, db: AsyncSession, status: str | None = None, statuses: list[str] | None = None
    ) -> list[Room]:
        """List rooms, optionally filtered by status or list of statuses."""
        stmt = select(Room).order_by(Room.created_at.desc())
        if statuses:
            stmt = stmt.where(Room.status.in_(statuses))
        elif status:
            stmt = stmt.where(Room.status == status)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ── Join / Leave ─────────────────────────────────────────

    async def join_room(
        self, db: AsyncSession, room_id: str, agent: Agent
    ) -> PlayerSlot:
        """Agent joins a room. Returns the assigned PlayerSlot."""
        room = await self.get_room(db, room_id)
        if room is None:
            raise ValueError("Room not found")
        if room.status != "waiting":
            raise ValueError(f"Cannot join room in status '{room.status}'")

        state = self._ensure_state(room)

        # Check if agent is already in the room
        existing = state.find_agent_slot(agent.id)
        if existing:
            raise ValueError("Agent already in this room")

        if state.is_full:
            raise ValueError("Room is full")

        slot = state.find_empty_slot()
        if slot is None:
            raise ValueError("No empty slot available")

        slot.agent_id = agent.id
        slot.agent_name = agent.name
        slot.status = "occupied"
        slot.connected_at = datetime.utcnow()

        # Update room status if full
        if state.is_full:
            room.status = "ready"

        logger.info(
            "Agent %s joined room %s at seat %d",
            agent.id, room_id, slot.seat,
        )
        return slot

    async def leave_room(
        self, db: AsyncSession, room_id: str, agent: Agent
    ) -> PlayerSlot:
        """Agent leaves a room. Returns the vacated PlayerSlot."""
        room = await self.get_room(db, room_id)
        if room is None:
            raise ValueError("Room not found")
        if room.status not in ("waiting", "ready"):
            raise ValueError(f"Cannot leave room in status '{room.status}'")

        state = self._ensure_state(room)
        slot = state.find_agent_slot(agent.id)
        if slot is None:
            raise ValueError("Agent is not in this room")

        slot.agent_id = None
        slot.agent_name = None
        slot.status = "empty"
        slot.connected_at = None

        # Room back to waiting if was ready
        if room.status == "ready":
            room.status = "waiting"

        logger.info("Agent %s left room %s from seat %d", agent.id, room_id, slot.seat)
        return slot

    # ── Ready / Unready ──────────────────────────────────────

    async def toggle_ready(
        self, db: AsyncSession, room_id: str, agent: Agent
    ) -> PlayerSlot:
        """Toggle agent's ready status. Returns the updated slot."""
        room = await self.get_room(db, room_id)
        if room is None:
            raise ValueError("Room not found")
        if room.status not in ("waiting", "ready"):
            raise ValueError(f"Cannot toggle ready in status '{room.status}'")

        state = self._ensure_state(room)
        slot = state.find_agent_slot(agent.id)
        if slot is None:
            raise ValueError("Agent is not in this room")

        if slot.status == "occupied":
            slot.status = "ready"
        elif slot.status == "ready":
            slot.status = "occupied"
        else:
            raise ValueError(f"Cannot toggle ready from status '{slot.status}'")

        return slot

    # ── Start Game ───────────────────────────────────────────

    async def start_game(
        self, db: AsyncSession, room_id: str
    ) -> Game:
        """Start a game in the room. Requires all slots filled and ready."""
        room = await self.get_room(db, room_id)
        if room is None:
            raise ValueError("Room not found")
        if room.status == "playing":
            raise ValueError("Game already in progress")
        if room.status != "ready":
            raise ValueError(f"Cannot start game in room status '{room.status}'")

        state = self._ensure_state(room)

        if not state.is_full:
            raise ValueError(
                f"Room not full ({state.occupied_count}/{state.player_count})"
            )
        if not state.all_ready:
            raise ValueError("Not all players are ready")

        # Resolve role assignment
        try:
            role_config = self._resolve_roles(room.config or {})
        except ValueError as e:
            raise ValueError(f"Role configuration error: {e}") from e

        # Shuffle and assign roles
        role_list: list[str] = []
        for role_name, count in role_config.items():
            role_list.extend([role_name] * count)
        random.shuffle(role_list)

        # Create Game record
        game = Game(
            room_id=room.id,
            status="in_progress",
            current_phase="waiting",
            current_round=0,
            role_config=role_config,
        )
        db.add(game)
        await db.flush()
        await db.refresh(game)

        # Create GamePlayer records
        for slot in state.slots:
            if slot.agent_id and slot.seat <= len(role_list):
                role_name = role_list[slot.seat - 1]
                player = GamePlayer(
                    game_id=game.id,
                    agent_id=slot.agent_id,
                    seat=slot.seat,
                    role=role_name,
                    is_alive=True,
                )
                db.add(player)

        # Update room status
        room.status = "playing"
        state.game_id = game.id

        await db.flush()

        logger.info(
            "Game %s started in room %s with roles: %s",
            game.id, room_id, role_config,
        )
        return game

    # ── State Queries ────────────────────────────────────────

    def get_room_state(self, room_id: str) -> RoomState | None:
        """Return the in-memory state for a room."""
        return self._rooms.get(room_id)

    def get_slots(self, room_id: str) -> list[PlayerSlot]:
        """Return the current slot list for a room."""
        state = self._rooms.get(room_id)
        if state is None:
            return []
        return state.slots

    def cleanup_room(self, room_id: str) -> None:
        """Remove in-memory state for a completed room."""
        self._rooms.pop(room_id, None)


# Singleton instance
room_manager = RoomManager()
