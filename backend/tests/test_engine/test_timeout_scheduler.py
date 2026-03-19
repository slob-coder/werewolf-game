"""Tests for the timeout scheduler."""

import asyncio

import pytest
import pytest_asyncio

from app.scheduler.timeout_scheduler import TimeoutScheduler


@pytest_asyncio.fixture
async def scheduler():
    s = TimeoutScheduler()
    yield s
    # Clean up any running timers
    for key, task in list(s._timers.items()):
        task.cancel()
    await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_schedule_fires(scheduler):
    fired = asyncio.Event()

    async def callback(game_id, phase):
        fired.set()

    await scheduler.schedule("game1", "night_werewolf", 0.05, callback)
    assert scheduler.is_pending("game1", "night_werewolf")

    await asyncio.wait_for(fired.wait(), timeout=1.0)
    assert fired.is_set()


@pytest.mark.asyncio
async def test_cancel(scheduler):
    fired = asyncio.Event()

    async def callback(game_id, phase):
        fired.set()

    await scheduler.schedule("game1", "night_werewolf", 0.1, callback)
    cancelled = await scheduler.cancel("game1", "night_werewolf")
    assert cancelled is True

    await asyncio.sleep(0.15)
    assert not fired.is_set()


@pytest.mark.asyncio
async def test_cancel_nonexistent(scheduler):
    cancelled = await scheduler.cancel("game1", "nonexistent")
    assert cancelled is False


@pytest.mark.asyncio
async def test_reschedule_replaces(scheduler):
    calls = []

    async def cb1(game_id, phase):
        calls.append("first")

    async def cb2(game_id, phase):
        calls.append("second")

    await scheduler.schedule("game1", "phase1", 0.1, cb1)
    await scheduler.schedule("game1", "phase1", 0.05, cb2)

    await asyncio.sleep(0.2)
    assert calls == ["second"]  # first was cancelled


@pytest.mark.asyncio
async def test_cancel_all(scheduler):
    fired = []

    async def cb(game_id, phase):
        fired.append((game_id, phase))

    await scheduler.schedule("game1", "p1", 0.1, cb)
    await scheduler.schedule("game1", "p2", 0.1, cb)
    await scheduler.schedule("game2", "p1", 0.1, cb)  # different game

    count = await scheduler.cancel_all("game1")
    assert count == 2

    await asyncio.sleep(0.2)
    # game1 timers should NOT have fired
    game1_fired = [(g, p) for g, p in fired if g == "game1"]
    assert game1_fired == []
    # game2 timer should have fired
    assert ("game2", "p1") in fired


@pytest.mark.asyncio
async def test_active_count(scheduler):
    async def noop(game_id, phase):
        pass

    await scheduler.schedule("g1", "p1", 10, noop)
    await scheduler.schedule("g1", "p2", 10, noop)
    assert scheduler.active_count == 2

    await scheduler.cancel("g1", "p1")
    assert scheduler.active_count == 1


@pytest.mark.asyncio
async def test_skip_zero_timeout(scheduler):
    fired = asyncio.Event()

    async def cb(game_id, phase):
        fired.set()

    await scheduler.schedule("g1", "p1", 0, cb)
    await asyncio.sleep(0.05)
    assert not fired.is_set()
    assert scheduler.active_count == 0


@pytest.mark.asyncio
async def test_callback_receives_kwargs(scheduler):
    received = {}

    async def cb(game_id, phase, **kwargs):
        received.update(kwargs)

    await scheduler.schedule("g1", "p1", 0.05, cb, extra_data="hello")
    await asyncio.sleep(0.15)
    assert received.get("extra_data") == "hello"
