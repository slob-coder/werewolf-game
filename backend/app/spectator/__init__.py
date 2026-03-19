"""Spectator package — replay and stats services."""

from app.spectator.replay import get_replay_data
from app.spectator.stats import get_game_stats

__all__ = ["get_replay_data", "get_game_stats"]
