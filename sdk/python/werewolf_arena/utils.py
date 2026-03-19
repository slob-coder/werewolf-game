"""Utility helpers for the Werewolf Arena SDK."""

from __future__ import annotations

import logging
import random
from typing import Sequence, Optional, List, Dict

logger = logging.getLogger(__name__)


def pick_random_target(candidates: Sequence[int], exclude: Optional[int] = None) -> Optional[int]:
    pool = [c for c in candidates if c != exclude]
    return random.choice(pool) if pool else None


def get_alive_seats(players: List[Dict]) -> List[int]:
    return [p["seat"] for p in players if p.get("is_alive", True)]


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
