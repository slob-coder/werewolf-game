"""API v1 router - Spectator endpoints.

GET /api/v1/games/{game_id}/replay  — full replay data
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND

from app.dependencies import get_db
from app.spectator.replay import get_replay_data

router = APIRouter(prefix="/api/v1/games", tags=["spectator"])


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
