"""API v1 router - Spectator endpoints.

GET /api/v1/games/{game_id}/spectate — live spectator snapshot
GET /api/v1/games/{game_id}/replay   — full replay data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND

from app.dependencies import get_db
from app.spectator.replay import get_replay_data
from app.spectator.service import spectator_service

router = APIRouter(prefix="/api/v1/games", tags=["spectator"])


@router.get("/{game_id}/spectate")
async def get_game_spectate(
    game_id: str,
    god_view: bool = Query(False, description="Show full role info (privileged)"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a live spectator snapshot of an ongoing game.

    Returns current phase, player statuses, and recent public events.
    Use ``god_view=true`` for full role visibility (requires elevated
    permissions in production).
    """
    snapshot = await spectator_service.get_spectate_snapshot(
        db, game_id, god_view=god_view
    )
    if snapshot is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )
    return snapshot


@router.get("/{game_id}/replay")
async def get_game_replay(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get full replay data for a completed game.

    Returns the complete event sequence with timestamps,
    player roles, and actions for replay visualization.
    """
    replay = await get_replay_data(db, game_id)
    if replay is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )
    return replay
