"""Win condition checker — determines if the game is over."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.roles.base import Faction

logger = logging.getLogger(__name__)


@dataclass
class WinResult:
    """Describes the game-over condition when one side wins."""

    winner: str  # "werewolf" | "villager" (good guys) | "draw"
    reason: str


@dataclass
class PlayerInfo:
    """Minimal player data needed for win checking."""

    seat: int
    role_name: str
    faction: Faction
    is_alive: bool


class WinChecker:
    """Checks win conditions after each settlement point.

    Win conditions:
    - All werewolves dead → good side wins
    - Werewolf count >= good side count → werewolf side wins
    """

    def check(self, players: list[PlayerInfo]) -> WinResult | None:
        """Return a ``WinResult`` if the game is over, else ``None``."""
        alive_werewolves = 0
        alive_good = 0  # villager + god

        for p in players:
            if not p.is_alive:
                continue
            if p.faction == Faction.WEREWOLF:
                alive_werewolves += 1
            else:
                alive_good += 1

        if alive_werewolves == 0:
            return WinResult(
                winner="villager",
                reason="所有狼人已出局，好人阵营获胜",
            )

        if alive_werewolves >= alive_good:
            return WinResult(
                winner="werewolf",
                reason=f"狼人数量（{alive_werewolves}）≥ 好人数量（{alive_good}），狼人阵营获胜",
            )

        return None
