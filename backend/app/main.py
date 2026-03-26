"""Werewolf Arena - FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.games import router as games_router
from app.api.v1.reports import router as reports_router
from app.api.v1.roles import router as roles_router
from app.api.v1.rooms import router as rooms_router
from app.api.v1.spectator import router as spectator_router
from app.api.v1.stats import game_router as stats_game_router, stats_router as stats_api_router
from app.config import settings
from app.websocket.event_bus import event_bus
from app.websocket.server import socket_app

# Ensure all models are imported so Alembic/metadata knows about them
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # Startup
    app.state.redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    # Start event bus
    await event_bus.start(app.state.redis)
    yield
    # Shutdown
    await event_bus.stop()
    await app.state.redis.close()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI Agent Werewolf Game Platform - Let AI agents play Werewolf!",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(rooms_router)
app.include_router(games_router)
app.include_router(roles_router)
app.include_router(spectator_router)
app.include_router(stats_game_router)
app.include_router(stats_api_router)
app.include_router(reports_router)

# Mount Socket.IO ASGI app
app.mount("/ws", socket_app)


# ── Health checks ────────────────────────────────────────────────

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Service health check."""
    return {"status": "ok", "service": "werewolf-arena"}


@app.get("/api/v1/health")
async def api_health_check() -> dict[str, str]:
    """API health check with version info."""
    return {
        "status": "ok",
        "service": "werewolf-arena",
        "version": "0.1.0",
    }
