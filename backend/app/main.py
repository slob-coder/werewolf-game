"""Werewolf Arena - FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # Startup
    app.state.redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    yield
    # Shutdown
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


# Health check endpoint
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
