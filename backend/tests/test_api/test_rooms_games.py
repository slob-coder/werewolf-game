"""Tests for room API endpoints and game API endpoints."""

import pytest
from httpx import AsyncClient


# ── Helpers ──────────────────────────────────────────────────────


async def _register_and_login(
    client: AsyncClient, username: str
) -> str:
    """Register + login, return JWT token."""
    await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "pass123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "pass123"},
    )
    return resp.json()["access_token"]


async def _create_agent(
    client: AsyncClient, token: str, name: str = "TestBot"
) -> tuple[str, str]:
    """Create an agent, return (agent_id, api_key)."""
    resp = await client.post(
        "/api/v1/agents",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    return data["id"], data["api_key"]


async def _create_room(
    client: AsyncClient,
    token: str,
    name: str = "TestRoom",
    player_count: int = 6,
) -> dict:
    """Create a room with the given params."""
    resp = await client.post(
        "/api/v1/rooms",
        json={
            "name": name,
            "player_count": player_count,
            "role_preset": "simple_6" if player_count == 6 else None,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()


# ── Role endpoints ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_role_presets(client: AsyncClient):
    """GET /api/v1/roles/presets returns presets."""
    resp = await client.get("/api/v1/roles/presets")
    assert resp.status_code == 200
    data = resp.json()
    assert "presets" in data
    assert len(data["presets"]) > 0
    # Check structure
    preset = data["presets"][0]
    assert "name" in preset
    assert "roles" in preset
    assert "player_count" in preset


@pytest.mark.asyncio
async def test_get_available_roles(client: AsyncClient):
    """GET /api/v1/roles/available returns available roles."""
    resp = await client.get("/api/v1/roles/available")
    assert resp.status_code == 200
    data = resp.json()
    assert "roles" in data
    assert len(data["roles"]) > 0
    role_names = {r["name"] for r in data["roles"]}
    assert "werewolf" in role_names
    assert "seer" in role_names
    assert "villager" in role_names


# ── Room CRUD ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_room(client: AsyncClient):
    """POST /api/v1/rooms creates a room."""
    token = await _register_and_login(client, "room_creator_1")
    data = await _create_room(client, token, "MyRoom", 6)
    assert data["name"] == "MyRoom"
    assert data["status"] == "open"
    assert data["player_count"] == 6
    assert data["current_players"] == 0
    assert len(data["slots"]) == 6


@pytest.mark.asyncio
async def test_list_rooms(client: AsyncClient):
    """GET /api/v1/rooms returns room list."""
    token = await _register_and_login(client, "room_lister_1")
    await _create_room(client, token, "ListRoom1", 6)
    await _create_room(client, token, "ListRoom2", 6)

    resp = await client.get("/api/v1/rooms")
    assert resp.status_code == 200
    rooms = resp.json()
    assert len(rooms) >= 2


@pytest.mark.asyncio
async def test_list_rooms_filter_status(client: AsyncClient):
    """GET /api/v1/rooms?status=open filters by status."""
    token = await _register_and_login(client, "room_filter_1")
    await _create_room(client, token, "FilterRoom", 6)

    resp = await client.get("/api/v1/rooms", params={"status": "open"})
    assert resp.status_code == 200
    for room in resp.json():
        assert room["status"] == "open"


@pytest.mark.asyncio
async def test_get_room_detail(client: AsyncClient):
    """GET /api/v1/rooms/{id} returns room details."""
    token = await _register_and_login(client, "room_detail_1")
    room = await _create_room(client, token, "DetailRoom", 6)

    resp = await client.get(f"/api/v1/rooms/{room['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == room["id"]
    assert data["name"] == "DetailRoom"


@pytest.mark.asyncio
async def test_get_room_not_found(client: AsyncClient):
    """GET /api/v1/rooms/{id} with bad ID returns 404."""
    resp = await client.get("/api/v1/rooms/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ── Join / Leave ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_join_room(client: AsyncClient):
    """POST /api/v1/rooms/{id}/join adds agent to room."""
    token = await _register_and_login(client, "join_user_1")
    _, api_key = await _create_agent(client, token, "JoinBot")
    room = await _create_room(client, token, "JoinRoom", 6)

    resp = await client.post(
        f"/api/v1/rooms/{room['id']}/join",
        headers={"X-Agent-Key": api_key},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["seat"] == 1
    assert data["room_id"] == room["id"]


@pytest.mark.asyncio
async def test_join_room_duplicate(client: AsyncClient):
    """Joining the same room twice returns 400."""
    token = await _register_and_login(client, "join_dup_user")
    _, api_key = await _create_agent(client, token, "DupBot")
    room = await _create_room(client, token, "DupRoom", 6)

    await client.post(
        f"/api/v1/rooms/{room['id']}/join",
        headers={"X-Agent-Key": api_key},
    )
    resp = await client.post(
        f"/api/v1/rooms/{room['id']}/join",
        headers={"X-Agent-Key": api_key},
    )
    assert resp.status_code == 400
    assert "already" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_leave_room(client: AsyncClient):
    """POST /api/v1/rooms/{id}/leave removes agent from room."""
    token = await _register_and_login(client, "leave_user_1")
    _, api_key = await _create_agent(client, token, "LeaveBot")
    room = await _create_room(client, token, "LeaveRoom", 6)

    await client.post(
        f"/api/v1/rooms/{room['id']}/join",
        headers={"X-Agent-Key": api_key},
    )
    resp = await client.post(
        f"/api/v1/rooms/{room['id']}/leave",
        headers={"X-Agent-Key": api_key},
    )
    assert resp.status_code == 200
    assert resp.json()["seat"] == 1


@pytest.mark.asyncio
async def test_leave_room_not_joined(client: AsyncClient):
    """Leaving a room you haven't joined returns 400."""
    token = await _register_and_login(client, "leave_nojoin_user")
    _, api_key = await _create_agent(client, token, "NoJoinBot")
    room = await _create_room(client, token, "NoJoinRoom", 6)

    resp = await client.post(
        f"/api/v1/rooms/{room['id']}/leave",
        headers={"X-Agent-Key": api_key},
    )
    assert resp.status_code == 400


# ── Ready ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_toggle_ready(client: AsyncClient):
    """POST /api/v1/rooms/{id}/ready toggles ready status."""
    token = await _register_and_login(client, "ready_user_1")
    _, api_key = await _create_agent(client, token, "ReadyBot")
    room = await _create_room(client, token, "ReadyRoom", 6)

    await client.post(
        f"/api/v1/rooms/{room['id']}/join",
        headers={"X-Agent-Key": api_key},
    )

    # Toggle to ready
    resp = await client.post(
        f"/api/v1/rooms/{room['id']}/ready",
        headers={"X-Agent-Key": api_key},
    )
    assert resp.status_code == 200
    assert resp.json()["is_ready"] is True

    # Toggle back to not ready
    resp = await client.post(
        f"/api/v1/rooms/{room['id']}/ready",
        headers={"X-Agent-Key": api_key},
    )
    assert resp.status_code == 200
    assert resp.json()["is_ready"] is False


# ── Start Game ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_game_not_full(client: AsyncClient):
    """Starting a game when room isn't full returns 400."""
    token = await _register_and_login(client, "start_notfull_user")
    room = await _create_room(client, token, "NotFullRoom", 6)

    resp = await client.post(f"/api/v1/rooms/{room['id']}/start")
    assert resp.status_code == 400
    assert "not full" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_full_game_flow(client: AsyncClient):
    """Full flow: create room, 6 agents join, ready up, start game."""
    token = await _register_and_login(client, "flow_user")
    room = await _create_room(client, token, "FlowRoom", 6)
    room_id = room["id"]

    # Create 6 agents, each joins and readies up
    api_keys = []
    for i in range(6):
        user_token = await _register_and_login(client, f"flow_agent_user_{i}")
        _, api_key = await _create_agent(client, user_token, f"FlowBot{i}")
        api_keys.append(api_key)

        join_resp = await client.post(
            f"/api/v1/rooms/{room_id}/join",
            headers={"X-Agent-Key": api_key},
        )
        assert join_resp.status_code == 200, f"Agent {i} join failed: {join_resp.json()}"

        ready_resp = await client.post(
            f"/api/v1/rooms/{room_id}/ready",
            headers={"X-Agent-Key": api_key},
        )
        assert ready_resp.status_code == 200

    # Start the game
    start_resp = await client.post(f"/api/v1/rooms/{room_id}/start")
    assert start_resp.status_code == 200
    game_data = start_resp.json()
    assert "game_id" in game_data
    assert game_data["message"] == "Game started"

    # Verify game state is accessible
    game_id = game_data["game_id"]
    state_resp = await client.get(
        f"/api/v1/games/{game_id}/state",
        headers={"X-Agent-Key": api_keys[0]},
    )
    assert state_resp.status_code == 200
    state = state_resp.json()
    assert state["game_id"] == game_id
    assert state["status"] == "in_progress"
    assert state["my_seat"] is not None
    assert state["my_role"] is not None
    assert len(state["players"]) == 6

    # Verify events endpoint works
    events_resp = await client.get(
        f"/api/v1/games/{game_id}/events",
        headers={"X-Agent-Key": api_keys[0]},
    )
    assert events_resp.status_code == 200
    assert events_resp.json()["game_id"] == game_id
