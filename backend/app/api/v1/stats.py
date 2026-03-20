"""API v1 router - Statistics endpoints.

GET /api/v1/games/{game_id}/stats       — game statistics panel data
GET /api/v1/stats/agents/{agent_id}     — per-agent career stats
GET /api/v1/stats/leaderboard           — agent leaderboard
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND

from app.dependencies import get_db
from app.models.agent import Agent
from app.spectator.stats import get_game_stats

game_router = APIRouter(prefix="/api/v1/games", tags=["statistics"])
stats_router = APIRouter(prefix="/api/v1/stats", tags=["statistics"])


@game_router.get("/{game_id}/stats")
async def get_game_statistics(
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


@stats_router.get("/agents/{agent_id}")
async def get_agent_stats(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get career statistics for a specific agent."""
    from app.agents.gateway import agent_gateway

    stats = await agent_gateway.get_agent_stats(db, agent_id)
    if stats is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )
    return stats


@stats_router.get("/leaderboard")
async def get_leaderboard(
    limit: int = Query(20, ge=1, le=100, description="Max entries"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get agent leaderboard sorted by win rate (min 3 games played)."""
    result = await db.execute(
        select(Agent)
        .where(
            Agent.is_active.is_(True),
            Agent.games_played >= 3,
        )
        .order_by(
            # win rate descending, then total games as tiebreaker
            desc(
                func.cast(Agent.games_won, func.Float)
                / func.nullif(Agent.games_played, 0)
            ),
            desc(Agent.games_played),
        )
        .limit(limit)
    )
    agents = result.scalars().all()

    leaderboard = []
    for rank, agent in enumerate(agents, start=1):
        played = agent.games_played or 0
        won = agent.games_won or 0
        win_rate = (won / played * 100) if played > 0 else 0.0
        leaderboard.append({
            "rank": rank,
            "agent_id": agent.id,
            "name": agent.name,
            "games_played": played,
            "games_won": won,
            "win_rate": round(win_rate, 1),
        })

    return leaderboard
