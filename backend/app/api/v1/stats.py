"""API v1 router - Statistics endpoints.

GET /api/v1/games/{game_id}/stats  — game statistics panel data
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND

from app.dependencies import get_db
from app.spectator.stats import get_game_stats

router = APIRouter(prefix="/api/v1/games", tags=["statistics"])


@router.get("/{game_id}/stats")
async def get_stats(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get statistics panel data for a game.

    Returns vote flow, identity guess heatmap, speech stats,
    and survival timeline.
    """
    stats = await get_game_stats(db, game_id)
    if stats is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )
    return stats
