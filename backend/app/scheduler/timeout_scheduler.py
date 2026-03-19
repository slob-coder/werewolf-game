"""Timeout scheduler — asyncio-based timers for game phase timeouts."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

# Type for the callback: async def callback(game_id, phase_key, **kwargs)
TimeoutCallback = Callable[..., Awaitable[None]]


class TimeoutScheduler:
    """Manages per-phase timeout timers using asyncio tasks.

    Each timer is keyed by ``"{game_id}:{phase}"``.  Scheduling a new
    timer for the same key cancels the previous one.
    """

    def __init__(self) -> None:
        self._timers: dict[str, asyncio.Task[None]] = {}

    # ── public API ────────────────────────────────────────────

    async def schedule(
        self,
        game_id: str,
        phase: str,
        timeout_seconds: int,
        callback: TimeoutCallback,
        **kwargs: Any,
    ) -> None:
        """Schedule (or reschedule) a timeout for a game phase."""
        key = f"{game_id}:{phase}"

        # Cancel existing timer for this key
        await self.cancel(game_id, phase)

        if timeout_seconds <= 0:
            logger.debug("Skipping timer for %s (timeout=%d)", key, timeout_seconds)
            return

        async def _timer() -> None:
            try:
                await asyncio.sleep(timeout_seconds)
                logger.info("Timeout fired for %s", key)
                await callback(game_id, phase, **kwargs)
            except asyncio.CancelledError:
                logger.debug("Timer cancelled for %s", key)
            except Exception:
                logger.exception("Error in timeout callback for %s", key)
            finally:
                self._timers.pop(key, None)

        task = asyncio.create_task(_timer(), name=f"timeout:{key}")
        self._timers[key] = task
        logger.debug("Timer set for %s (%ds)", key, timeout_seconds)

    async def cancel(self, game_id: str, phase: str) -> bool:
        """Cancel a pending timer.  Returns True if one was cancelled."""
        key = f"{game_id}:{phase}"
        task = self._timers.pop(key, None)
        if task is not None and not task.done():
            task.cancel()
            return True
        return False

    async def cancel_all(self, game_id: str) -> int:
        """Cancel all timers for a game.  Returns count cancelled."""
        prefix = f"{game_id}:"
        cancelled = 0
        keys = [k for k in self._timers if k.startswith(prefix)]
        for key in keys:
            task = self._timers.pop(key, None)
            if task is not None and not task.done():
                task.cancel()
                cancelled += 1
        return cancelled

    def is_pending(self, game_id: str, phase: str) -> bool:
        key = f"{game_id}:{phase}"
        task = self._timers.get(key)
        return task is not None and not task.done()

    @property
    def active_count(self) -> int:
        return sum(1 for t in self._timers.values() if not t.done())
