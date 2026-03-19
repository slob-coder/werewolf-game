"""Information filter — filters game state and events by player visibility.

Visibility levels:
  - public:  visible to everyone
  - role:    visible to same faction (werewolves see each other)
  - private: only visible to the specific player
  - god:     visible only to spectators / god view
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.roles.base import Faction

logger = logging.getLogger(__name__)


@dataclass
class PlayerContext:
    """Context about the requesting player for filtering decisions."""

    seat: int
    role: str
    faction: str  # "werewolf" | "villager" | "god"
    is_alive: bool
    is_spectator: bool = False  # True = god view


class InformationFilter:
    """Filters game state and events based on player role and visibility rules.

    Rules:
    - Werewolves can see their teammates' roles
    - Villagers and god-faction roles only see their own role
    - Dead players get expanded visibility (can see roles of other dead players)
    - Spectators (god view) see everything
    - Events are filtered by visibility tag: public/role/private/god
    """

    # ── Game state filtering ─────────────────────────────────

    def filter_game_state(
        self,
        players: list[dict[str, Any]],
        ctx: PlayerContext,
    ) -> list[dict[str, Any]]:
        """Filter player list: mask roles based on viewer's context.

        Each player dict should have keys: seat, agent_name, is_alive, role, faction.
        Returns list with role possibly masked.
        """
        if ctx.is_spectator:
            # God view — show everything
            return players

        filtered = []
        for p in players:
            entry = {
                "seat": p["seat"],
                "agent_name": p.get("agent_name"),
                "is_alive": p["is_alive"],
                "role": None,  # hidden by default
            }

            # Always see own role
            if p["seat"] == ctx.seat:
                entry["role"] = p["role"]
            # Werewolves see fellow werewolves
            elif ctx.faction == Faction.WEREWOLF and p.get("faction") == Faction.WEREWOLF:
                entry["role"] = p["role"]
            # Dead players can see other dead players' roles
            elif not ctx.is_alive and not p["is_alive"]:
                entry["role"] = p["role"]

            filtered.append(entry)

        return filtered

    # ── Event filtering ──────────────────────────────────────

    def filter_event(
        self,
        event: dict[str, Any],
        ctx: PlayerContext,
    ) -> dict[str, Any] | None:
        """Filter a single event based on visibility.

        Returns the (possibly modified) event, or None if hidden.
        """
        visibility = event.get("visibility", "public")

        if ctx.is_spectator:
            return event  # God view sees all

        if visibility == "public":
            return event

        if visibility == "god":
            return None  # Only spectators see god-level events

        if visibility == "private":
            # Only the target player can see it
            target_seat = event.get("data", {}).get("target_seat")
            actor_seat = event.get("data", {}).get("actor_seat")
            if ctx.seat in (target_seat, actor_seat):
                return event
            return None

        if visibility == "role":
            # Faction-based: werewolves see werewolf events
            event_faction = event.get("data", {}).get("faction")
            if event_faction and ctx.faction == event_faction:
                return event
            # Dead players see role-level events
            if not ctx.is_alive:
                return event
            return None

        # Unknown visibility — treat as hidden
        return None

    # ── Bulk event filtering ─────────────────────────────────

    def filter_events(
        self,
        events: list[dict[str, Any]],
        ctx: PlayerContext,
    ) -> list[dict[str, Any]]:
        """Filter a list of events, removing hidden ones."""
        result = []
        for ev in events:
            filtered = self.filter_event(ev, ctx)
            if filtered is not None:
                result.append(filtered)
        return result


# ── Content filter (configurable content auditing) ───────────────

import re


class ContentCheckResult:
    """Result of content auditing."""

    def __init__(self, passed: bool, reason: str = ""):
        self.passed = passed
        self.reason = reason


class ContentFilter:
    """Prevents agents from leaking system message formats or private info
    through speech content.  Only active when room config enables it.
    """

    FORBIDDEN_PATTERNS: list[str] = [
        r"event_type.*phase\.night",
        r"action_type.*werewolf_kill",
        r"target_seat.*\d+.*action_type",
        r"seer_check.*result",
        r"\bapi_key\b",
        r"\bX-Agent-Key\b",
    ]

    _compiled: list[re.Pattern[str]] | None = None

    @classmethod
    def _get_patterns(cls) -> list[re.Pattern[str]]:
        if cls._compiled is None:
            cls._compiled = [
                re.compile(p, re.IGNORECASE) for p in cls.FORBIDDEN_PATTERNS
            ]
        return cls._compiled

    @classmethod
    def check(cls, content: str, player_role: str | None = None) -> ContentCheckResult:
        """Check speech content for forbidden patterns.

        Returns ContentCheckResult with passed=False if content violates rules.
        """
        if not content:
            return ContentCheckResult(passed=True)

        for pattern in cls._get_patterns():
            if pattern.search(content):
                return ContentCheckResult(
                    passed=False,
                    reason=f"Content contains forbidden pattern: {pattern.pattern}",
                )

        # Length check — unreasonably long speech
        if len(content) > 5000:
            return ContentCheckResult(
                passed=False,
                reason="Content exceeds maximum length (5000 characters)",
            )

        return ContentCheckResult(passed=True)


# Singleton
information_filter = InformationFilter()
