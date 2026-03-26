"""API v1 router - Room management endpoints."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from app.dependencies import get_current_agent, get_current_user, get_db
from app.engine.game_engine import engine_registry
from app.models.agent import Agent
from app.models.user import User
from app.rooms.manager import room_manager
from app.scheduler.timeout_scheduler import TimeoutScheduler
from app.schemas.room import (
    PlayerSlotResponse,
    RoomCreateRequest,
    RoomJoinResponse,
    RoomListResponse,
    RoomReadyResponse,
    RoomResponse,
    RoomStartResponse,
)
from app.websocket.event_bus import event_bus
from app.websocket.reconnection import reconnection_manager

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])


# ── Helpers ──────────────────────────────────────────────────────


def _build_room_response(room, slots) -> RoomResponse:
    """Build a RoomResponse from a Room model and slot list."""
    config = room.config or {}
    player_count = config.get("player_count", 9)
    current_players = sum(1 for s in slots if s.status != "empty")
    
    # Find current in-progress game (latest one if multiple)
    current_game_id = None
    if room.games:
        # Get the most recent in-progress game
        in_progress_games = [
            g for g in room.games 
            if g.status == "in_progress"
        ]
        if in_progress_games:
            # Sort by started_at descending, take the first
            current_game_id = sorted(
                in_progress_games, 
                key=lambda g: g.started_at, 
                reverse=True
            )[0].id
    
    return RoomResponse(
        id=room.id,
        name=room.name,
        status=room.status,
        config=config,
        created_by=room.created_by,
        created_at=room.created_at,
        player_count=player_count,
        current_players=current_players,
        slots=[
            PlayerSlotResponse(
                seat=s.seat,
                agent_id=s.agent_id,
                agent_name=s.agent_name,
                status=s.status,
            )
            for s in slots
        ],
        current_game_id=current_game_id,
    )


def _build_list_item(room, slots) -> RoomListResponse:
    config = room.config or {}
    player_count = config.get("player_count", 9)
    current_players = sum(1 for s in slots if s.status != "empty")
    return RoomListResponse(
        id=room.id,
        name=room.name,
        status=room.status,
        player_count=player_count,
        current_players=current_players,
        created_at=room.created_at,
    )


# ── Endpoints ────────────────────────────────────────────────────


@router.post("", response_model=RoomResponse, status_code=201)
async def create_room(
    body: RoomCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new game room."""
    room = await room_manager.create_room(db, body, created_by=current_user.id)
    slots = room_manager.get_slots(room.id)
    return _build_room_response(room, slots)


@router.get("", response_model=list[RoomListResponse])
async def list_rooms(
    status: str | None = Query(None, description="Filter by room status"),
    db: AsyncSession = Depends(get_db),
):
    """List rooms with optional status filter. Defaults to showing joinable rooms."""
    # Default: show waiting and ready rooms (joinable/watchable)
    if status is None:
        rooms = await room_manager.list_rooms(db, statuses=["waiting", "ready"])
    else:
        rooms = await room_manager.list_rooms(db, status=status)
    result = []
    for r in rooms:
        slots = room_manager.get_slots(r.id)
        result.append(_build_list_item(r, slots))
    return result


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get room details by ID."""
    # 使用 selectinload 预加载 games 关系，避免 N+1 查询
    from app.models.room import Room as RoomModel
    stmt = (
        select(RoomModel)
        .where(RoomModel.id == room_id)
        .options(selectinload(RoomModel.games))
    )
    result = await db.execute(stmt)
    room = result.scalar_one_or_none()
    
    if room is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Room not found")
    # Ensure in-memory state is initialized
    room_manager._ensure_state(room)
    slots = room_manager.get_slots(room.id)
    return _build_room_response(room, slots)


@router.post("/{room_id}/join", response_model=RoomJoinResponse)
async def join_room(
    room_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Agent joins a room. Requires X-Agent-Key header."""
    try:
        slot = await room_manager.join_room(db, room_id, agent)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))

    return RoomJoinResponse(
        seat=slot.seat,
        room_id=room_id,
        agent_id=agent.id,
        message=f"Joined room at seat {slot.seat}",
    )


@router.post("/{room_id}/leave")
async def leave_room(
    room_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Agent leaves a room. Requires X-Agent-Key header."""
    try:
        slot = await room_manager.leave_room(db, room_id, agent)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))

    return {"message": f"Left room from seat {slot.seat}", "seat": slot.seat}


@router.post("/{room_id}/ready", response_model=RoomReadyResponse)
async def toggle_ready(
    room_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Toggle agent's ready status. Requires X-Agent-Key header."""
    try:
        slot = await room_manager.toggle_ready(db, room_id, agent)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))

    is_ready = slot.status == "ready"
    return RoomReadyResponse(
        seat=slot.seat,
        room_id=room_id,
        is_ready=is_ready,
        message="Ready" if is_ready else "Not ready",
    )


@router.post("/{room_id}/start", response_model=RoomStartResponse)
async def start_game(
    room_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Start the game in a room. Room must be full with all players ready.

    Creates DB records via RoomManager, then initialises a GameEngine
    instance which drives the entire game lifecycle (phase transitions,
    timeout scheduling, event broadcasting).
    """
    try:
        game = await room_manager.start_game(db, room_id)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))

    # Create and register a GameEngine for this game
    scheduler = TimeoutScheduler()
    engine = engine_registry.create(
        game.id,
        event_bus=event_bus,
        scheduler=scheduler,
        reconnection_manager=reconnection_manager,
    )

    # Kick off the game lifecycle in a background task so the HTTP
    # response returns immediately.
    asyncio.create_task(
        engine.start_game(),
        name=f"game-engine:{game.id}",
    )

    return RoomStartResponse(
        room_id=room_id,
        game_id=game.id,
        message="Game started",
    )
