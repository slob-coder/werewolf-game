"""Statistics panel data — vote flow, identity heatmap, speech stats.

Provides the stats data for GET /api/v1/games/{id}/stats.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action import GameAction
from app.models.event import GameEvent
from app.models.game import Game
from app.models.player import GamePlayer

logger = logging.getLogger(__name__)


async def get_game_stats(
    db: AsyncSession, game_id: str
) -> dict[str, Any] | None:
    """Build statistics data for a game.

    Returns vote flow, identity guess heatmap, speech stats,
    and survival timeline, or None if the game doesn't exist.
    """
    # Fetch game
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if game is None:
        return None

    # Fetch players
    players_result = await db.execute(
        select(GamePlayer)
        .where(GamePlayer.game_id == game_id)
        .order_by(GamePlayer.seat)
    )
    players = players_result.scalars().all()
    seat_to_role = {p.seat: p.role for p in players}
    seat_to_agent = {p.seat: p.agent_id for p in players}
    player_id_to_seat = {p.id: p.seat for p in players}

    # Fetch all actions
    actions_result = await db.execute(
        select(GameAction)
        .where(GameAction.game_id == game_id)
        .order_by(GameAction.timestamp)
    )
    actions = actions_result.scalars().all()

    # ── Vote flow stats ──────────────────────────────────────
    vote_flow = _compute_vote_flow(actions, player_id_to_seat)

    # ── Identity guess heatmap ───────────────────────────────
    identity_heatmap = _compute_identity_heatmap(actions, player_id_to_seat, seat_to_role)

    # ── Speech stats ─────────────────────────────────────────
    speech_stats = _compute_speech_stats(actions, player_id_to_seat)

    # ── Survival timeline ────────────────────────────────────
    survival_timeline = _compute_survival_timeline(players)

    return {
        "game_id": game_id,
        "status": game.status,
        "winner": game.winner,
        "total_rounds": game.current_round,
        "vote_flow": vote_flow,
        "identity_heatmap": identity_heatmap,
        "speech_stats": speech_stats,
        "survival_timeline": survival_timeline,
        "player_roles": {str(seat): role for seat, role in seat_to_role.items()},
    }


def _compute_vote_flow(
    actions: list[GameAction],
    player_id_to_seat: dict[str, int],
) -> list[dict[str, Any]]:
    """Compute per-round vote flow data for Sankey-style visualization."""
    rounds: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for action in actions:
        if action.action_type not in ("vote", "vote_abstain"):
            continue

        voter_seat = player_id_to_seat.get(action.player_id)
        if voter_seat is None:
            continue

        vote_entry: dict[str, Any] = {
            "voter_seat": voter_seat,
            "target_seat": action.target_seat,
            "is_abstain": action.action_type == "vote_abstain",
            "is_timeout": action.is_timeout,
        }
        rounds[action.round].append(vote_entry)

    return [
        {"round": r, "votes": votes}
        for r, votes in sorted(rounds.items())
    ]


def _compute_identity_heatmap(
    actions: list[GameAction],
    player_id_to_seat: dict[str, int],
    seat_to_role: dict[int, str],
) -> dict[str, Any]:
    """Compute identity guess heatmap based on vote targets.

    The heatmap shows how often each player voted for each other player,
    which can be used to infer suspicion patterns.
    """
    # Matrix: suspicion[voter_seat][target_seat] = count
    suspicion: dict[int, Counter[int]] = defaultdict(Counter)

    for action in actions:
        if action.action_type != "vote" or action.target_seat is None:
            continue
        voter_seat = player_id_to_seat.get(action.player_id)
        if voter_seat is None:
            continue
        suspicion[voter_seat][action.target_seat] += 1

    # Convert to serializable format
    matrix = []
    for voter_seat, targets in sorted(suspicion.items()):
        for target_seat, count in sorted(targets.items()):
            matrix.append({
                "voter_seat": voter_seat,
                "voter_role": seat_to_role.get(voter_seat),
                "target_seat": target_seat,
                "target_role": seat_to_role.get(target_seat),
                "count": count,
            })

    return {
        "matrix": matrix,
        "total_votes": sum(c for targets in suspicion.values() for c in targets.values()),
    }


def _compute_speech_stats(
    actions: list[GameAction],
    player_id_to_seat: dict[str, int],
) -> list[dict[str, Any]]:
    """Compute per-player speech statistics."""
    stats: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "total_length": 0, "max_length": 0}
    )

    for action in actions:
        if action.action_type != "speech":
            continue
        seat = player_id_to_seat.get(action.player_id)
        if seat is None:
            continue

        content_len = len(action.content or "")
        stats[seat]["count"] += 1
        stats[seat]["total_length"] += content_len
        stats[seat]["max_length"] = max(stats[seat]["max_length"], content_len)

    result = []
    for seat, s in sorted(stats.items()):
        avg_len = s["total_length"] / s["count"] if s["count"] > 0 else 0
        result.append({
            "seat": seat,
            "speech_count": s["count"],
            "total_length": s["total_length"],
            "average_length": round(avg_len, 1),
            "max_length": s["max_length"],
        })

    return result


def _compute_survival_timeline(
    players: list[GamePlayer],
) -> list[dict[str, Any]]:
    """Compute survival timeline data.

    Shows when each player died, organized by round.
    """
    timeline: dict[int, list[dict[str, Any]]] = defaultdict(list)

    alive_count = len(players)
    # Round 0 = game start
    werewolf_count = sum(1 for p in players if p.role == "werewolf")
    villager_count = alive_count - werewolf_count

    timeline[0] = [{
        "event": "game_start",
        "alive_total": alive_count,
        "alive_werewolf": werewolf_count,
        "alive_villager": villager_count,
    }]

    for p in sorted(players, key=lambda x: x.death_round or 999):
        if p.death_round is not None:
            if p.role == "werewolf":
                werewolf_count -= 1
            else:
                villager_count -= 1
            alive_count -= 1

            timeline[p.death_round].append({
                "event": "player_death",
                "seat": p.seat,
                "role": p.role,
                "cause": p.death_cause,
                "alive_total": alive_count,
                "alive_werewolf": werewolf_count,
                "alive_villager": villager_count,
            })

    return [
        {"round": r, "events": evts}
        for r, evts in sorted(timeline.items())
    ]
