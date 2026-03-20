"""API v1 router - Game operation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from app.dependencies import get_current_agent, get_db
from app.engine.game_engine import engine_registry
from app.engine.information_filter import (
    ContentFilter,
    PlayerContext,
    information_filter,
)
from app.models.agent import Agent
from app.models.event import GameEvent
from app.models.game import Game
from app.models.player import GamePlayer
from app.roles.base import ActionType, Faction
from app.roles.registry import RoleRegistry
from app.schemas.game import (
    ActionRequest,
    ActionResponse,
    GameEventResponse,
    GameEventsListResponse,
    GameStateResponse,
    PlayerStateResponse,
)

router = APIRouter(prefix="/api/v1/games", tags=["games"])


# ── Helpers ──────────────────────────────────────────────────────


async def _get_game(db: AsyncSession, game_id: str) -> Game:
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Game not found")
    return game


async def _get_player_in_game(
    db: AsyncSession, game_id: str, agent_id: str
) -> GamePlayer:
    result = await db.execute(
        select(GamePlayer).where(
            GamePlayer.game_id == game_id,
            GamePlayer.agent_id == agent_id,
        )
    )
    player = result.scalar_one_or_none()
    if player is None:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Agent is not a player in this game",
        )
    return player


def _build_player_context(player: GamePlayer) -> PlayerContext:
    """Build PlayerContext from a GamePlayer for information filtering."""
    role_cls = RoleRegistry.get(player.role)
    faction = role_cls.faction if role_cls else Faction.VILLAGER
    return PlayerContext(
        seat=player.seat,
        role=player.role,
        faction=faction,
        is_alive=player.is_alive,
    )


# ── Endpoints ────────────────────────────────────────────────────


@router.post("/{game_id}/action", response_model=ActionResponse)
async def submit_action(
    game_id: str,
    body: ActionRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Agent submits a game action.

    The action is routed through the active GameEngine instance which
    handles validation, side-effects, phase completion, and event
    broadcasting.
    """
    game = await _get_game(db, game_id)

    if game.status != "in_progress":
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Game is not in progress",
        )

    player = await _get_player_in_game(db, game_id, agent.id)

    # Content filter check for speech/chat actions
    try:
        action_type = ActionType(body.action_type)
    except ValueError:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Unknown action type: {body.action_type}",
        )

    if action_type in (ActionType.SPEECH, ActionType.WEREWOLF_CHAT, ActionType.LAST_WORDS):
        if body.content:
            check_result = ContentFilter.check(body.content, player.role)
            if not check_result.passed:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Content rejected: {check_result.reason}",
                )

    # Route to GameEngine
    engine = engine_registry.get(game_id)
    if engine is None:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="No active game engine for this game",
        )

    result = await engine.process_action(
        player_id=player.id,
        action_type_str=body.action_type,
        target_seat=body.target_seat,
        content=body.content,
    )

    return ActionResponse(
        success=result["success"],
        action_id=result.get("action_id"),
        message=result["message"],
    )


@router.get("/{game_id}/state", response_model=GameStateResponse)
async def get_game_state(
    game_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Get filtered game state from the agent's perspective."""
    game = await _get_game(db, game_id)
    player = await _get_player_in_game(db, game_id, agent.id)

    # Build player context for filtering
    ctx = _build_player_context(player)

    # Fetch all players
    result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == game_id)
    )
    all_players = result.scalars().all()

    # Build raw player data
    raw_players = []
    for p in all_players:
        role_cls = RoleRegistry.get(p.role)
        faction = role_cls.faction if role_cls else Faction.VILLAGER
        raw_players.append({
            "seat": p.seat,
            "agent_name": p.agent.name if p.agent else None,
            "is_alive": p.is_alive,
            "role": p.role,
            "faction": faction,
        })

    # Filter through information filter
    filtered_players = information_filter.filter_game_state(raw_players, ctx)

    return GameStateResponse(
        game_id=game.id,
        room_id=game.room_id,
        status=game.status,
        current_phase=game.current_phase,
        current_round=game.current_round,
        my_seat=player.seat,
        my_role=player.role,
        players=[
            PlayerStateResponse(
                seat=p["seat"],
                agent_name=p.get("agent_name"),
                is_alive=p["is_alive"],
                role=p.get("role"),
            )
            for p in filtered_players
        ],
        started_at=game.started_at,
        finished_at=game.finished_at,
        winner=game.winner,
    )


@router.get("/{game_id}/events", response_model=GameEventsListResponse)
async def get_game_events(
    game_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Get filtered event history from the agent's perspective."""
    game = await _get_game(db, game_id)
    player = await _get_player_in_game(db, game_id, agent.id)

    ctx = _build_player_context(player)

    # Fetch all events
    result = await db.execute(
        select(GameEvent)
        .where(GameEvent.game_id == game_id)
        .order_by(GameEvent.timestamp)
    )
    all_events = result.scalars().all()

    # Convert to dicts for filtering
    raw_events = [
        {
            "id": ev.id,
            "event_type": ev.event_type,
            "round": ev.round,
            "phase": ev.phase,
            "data": ev.data,
            "visibility": ev.visibility,
            "timestamp": ev.timestamp,
        }
        for ev in all_events
    ]

    # Filter events
    filtered = information_filter.filter_events(raw_events, ctx)

    return GameEventsListResponse(
        game_id=game_id,
        events=[
            GameEventResponse(
                id=ev["id"],
                event_type=ev["event_type"],
                round=ev["round"],
                phase=ev["phase"],
                data=ev["data"],
                visibility=ev["visibility"],
                timestamp=ev["timestamp"],
            )
            for ev in filtered
        ],
    )
