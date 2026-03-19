"""Tests for authentication and agent management endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """POST /api/v1/auth/register creates a user and returns user data."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser1", "password": "secret123", "email": "t1@example.com"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "testuser1"
    assert data["email"] == "t1@example.com"
    assert data["role"] == "user"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    """Registering the same username twice returns 400."""
    await client.post(
        "/api/v1/auth/register",
        json={"username": "dupuser", "password": "secret123"},
    )
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": "dupuser", "password": "otherpass"},
    )
    assert resp.status_code == 400
    assert "already taken" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """POST /api/v1/auth/login returns a JWT token for valid credentials."""
    await client.post(
        "/api/v1/auth/register",
        json={"username": "loginuser", "password": "mypassword"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "loginuser", "password": "mypassword"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    """Login with wrong password returns 400."""
    await client.post(
        "/api/v1/auth/register",
        json={"username": "loginuser2", "password": "correct"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "loginuser2", "password": "wrong"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    """GET /api/v1/auth/me returns the current user when authenticated."""
    await client.post(
        "/api/v1/auth/register",
        json={"username": "meuser", "password": "pass123"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "meuser", "password": "pass123"},
    )
    token = login_resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "meuser"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    """GET /api/v1/auth/me without token returns 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ── Agent management ─────────────────────────────────────────────


async def _get_token(client: AsyncClient, username: str = "agentowner") -> str:
    """Helper: register + login and return the JWT token."""
    await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "pass123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "pass123"},
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_agent(client: AsyncClient):
    """POST /api/v1/agents creates an agent and returns the API key."""
    token = await _get_token(client, "createagentuser")
    resp = await client.post(
        "/api/v1/agents",
        json={"name": "MyBot", "description": "A test bot"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "MyBot"
    assert "api_key" in data  # shown only on creation
    assert len(data["api_key"]) > 20


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient):
    """GET /api/v1/agents returns agents owned by the current user."""
    token = await _get_token(client, "listagentuser")
    # Create two agents
    await client.post(
        "/api/v1/agents",
        json={"name": "Bot1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/agents",
        json={"name": "Bot2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        "/api/v1/agents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) >= 2
    names = {a["name"] for a in agents}
    assert "Bot1" in names
    assert "Bot2" in names


@pytest.mark.asyncio
async def test_delete_agent(client: AsyncClient):
    """DELETE /api/v1/agents/{id} soft-deletes the agent."""
    token = await _get_token(client, "deleteagentuser")
    create_resp = await client.post(
        "/api/v1/agents",
        json={"name": "ToDelete"},
        headers={"Authorization": f"Bearer {token}"},
    )
    agent_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/agents/{agent_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204

    # Listing should no longer include the deleted agent
    list_resp = await client.get(
        "/api/v1/agents",
        headers={"Authorization": f"Bearer {token}"},
    )
    ids = {a["id"] for a in list_resp.json()}
    assert agent_id not in ids


@pytest.mark.asyncio
async def test_delete_agent_not_found(client: AsyncClient):
    """Deleting a non-existent agent returns 404."""
    token = await _get_token(client, "del404user")
    resp = await client.delete(
        "/api/v1/agents/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
