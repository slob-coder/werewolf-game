"""Tests for server exception tracking endpoints."""

import base64
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.server_exception import ServerException


async def _get_captcha(client: AsyncClient) -> tuple[str, str]:
    """Helper: get captcha and return (captcha_id, captcha_code)."""
    resp = await client.get("/api/v1/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()
    captcha_id = data["captcha_id"]
    captcha_image = data["captcha_image"]
    
    # Extract code from base64 image (fallback mode stores code as text)
    if captcha_image.startswith("data:text/plain;base64,"):
        code = base64.b64decode(captcha_image.split(",", 1)[1]).decode()
    else:
        # For real captcha images, access the store directly
        from app.api.v1.auth import _captcha_store
        stored = _captcha_store.get(captcha_id)
        if stored:
            code = stored[0]
        else:
            raise ValueError("Could not get captcha code from store")
    
    return captcha_id, code


async def _get_token(client: AsyncClient, username: str = "exceptionuser") -> str:
    """Helper: register + login and return the JWT token."""
    captcha_id, captcha_code = await _get_captcha(client)
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "pass123",
            "captcha_id": captcha_id,
            "captcha_code": captcha_code,
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "pass123"},
    )
    return resp.json()["access_token"]


# ── Test List Exceptions ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_exceptions_empty(client: AsyncClient):
    """GET /api/v1/server-exceptions returns empty list when no exceptions."""
    token = await _get_token(client, "listemptyuser")
    resp = await client.get(
        "/api/v1/server-exceptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["exceptions"] == []


@pytest.mark.asyncio
async def test_list_exceptions_unauthenticated(client: AsyncClient):
    """GET /api/v1/server-exceptions requires authentication."""
    resp = await client.get("/api/v1/server-exceptions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_exceptions_pagination(client: AsyncClient):
    """GET /api/v1/server-exceptions supports pagination."""
    token = await _get_token(client, "paginationuser")
    resp = await client.get(
        "/api/v1/server-exceptions?limit=10&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "exceptions" in data


# ── Test Get Stats ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_exception_stats(client: AsyncClient):
    """GET /api/v1/server-exceptions/stats returns statistics."""
    token = await _get_token(client, "statsuser")
    resp = await client.get(
        "/api/v1/server-exceptions/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_exceptions" in data
    assert "by_type" in data
    assert "unresolved" in data
    assert "recent_exceptions" in data


@pytest.mark.asyncio
async def test_get_exception_stats_unauthenticated(client: AsyncClient):
    """GET /api/v1/server-exceptions/stats requires authentication."""
    resp = await client.get("/api/v1/server-exceptions/stats")
    assert resp.status_code == 401


# ── Test Get Single Exception ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_exception_not_found(client: AsyncClient):
    """GET /api/v1/server-exceptions/{id} returns 404 for non-existent."""
    token = await _get_token(client, "getnotfounduser")
    
    resp = await client.get(
        f"/api/v1/server-exceptions/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_exception_unauthenticated(client: AsyncClient):
    """GET /api/v1/server-exceptions/{id} requires authentication."""
    resp = await client.get(f"/api/v1/server-exceptions/{uuid4()}")
    assert resp.status_code == 401


# ── Test Resolve Exception ────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_exception_not_found(client: AsyncClient):
    """PATCH resolve returns 404 for non-existent exception."""
    token = await _get_token(client, "resolvenotfounduser")
    
    resp = await client.patch(
        f"/api/v1/server-exceptions/{uuid4()}/resolve",
        json={"note": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resolve_exception_unauthenticated(client: AsyncClient):
    """PATCH resolve requires authentication."""
    resp = await client.patch(
        f"/api/v1/server-exceptions/{uuid4()}/resolve",
        json={"note": "Test"},
    )
    assert resp.status_code == 401


# ── Test Delete Exception ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_exception_not_found(client: AsyncClient):
    """DELETE returns 404 for non-existent exception."""
    token = await _get_token(client, "deletenotfounduser")
    
    resp = await client.delete(
        f"/api/v1/server-exceptions/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_exception_unauthenticated(client: AsyncClient):
    """DELETE requires authentication."""
    resp = await client.delete(f"/api/v1/server-exceptions/{uuid4()}")
    assert resp.status_code == 401


# ── Test Bulk Delete ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bulk_delete_resolved(client: AsyncClient):
    """DELETE /api/v1/server-exceptions deletes old resolved exceptions."""
    token = await _get_token(client, "bulkdeleteuser")
    
    resp = await client.delete(
        "/api/v1/server-exceptions?older_than_days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "deleted" in data


@pytest.mark.asyncio
async def test_bulk_delete_unauthenticated(client: AsyncClient):
    """Bulk delete requires authentication."""
    resp = await client.delete("/api/v1/server-exceptions")
    assert resp.status_code == 401
