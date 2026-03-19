"""Pytest configuration and shared fixtures.

Uses an in-process SQLite database for fast unit tests.
For full integration tests against PostgreSQL, set TEST_DATABASE_URL.
"""

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.dependencies import get_db
from app.main import app

# Use SQLite for tests unless a Postgres URL is provided
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///./test.db",
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_db():
    """Create all tables once before tests, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = _override_get_db


# ── Fake Redis that stores in memory ────────────────────────────

class FakeRedis:
    """Minimal in-memory Redis stub for rate limiter tests."""

    def __init__(self):
        self._data: dict = {}

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, redis: FakeRedis):
        self._redis = redis
        self._commands: list = []

    def zremrangebyscore(self, key, _min, _max):
        self._commands.append(("zremrangebyscore", key, _min, _max))
        return self

    def zcard(self, key):
        self._commands.append(("zcard", key))
        return self

    def zadd(self, key, mapping):
        self._commands.append(("zadd", key, mapping))
        return self

    def expire(self, key, seconds):
        self._commands.append(("expire", key, seconds))
        return self

    async def execute(self):
        results = []
        for cmd in self._commands:
            if cmd[0] == "zremrangebyscore":
                # no-op
                results.append(0)
            elif cmd[0] == "zcard":
                results.append(0)  # always under limit
            elif cmd[0] == "zadd":
                results.append(1)
            elif cmd[0] == "expire":
                results.append(True)
        return results


@pytest_asyncio.fixture(autouse=True)
async def _patch_redis():
    """Inject a fake Redis so rate limiter doesn't need a real server."""
    app.state.redis = FakeRedis()
    yield


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
