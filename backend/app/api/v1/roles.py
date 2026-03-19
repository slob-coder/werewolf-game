"""API v1 router - Role configuration endpoints."""

from fastapi import APIRouter

from app.roles.registry import RoleRegistry
from app.rooms.manager import ROLE_PRESETS
from app.schemas.role import (
    AvailableRolesResponse,
    RoleInfo,
    RolePreset,
    RolePresetsResponse,
)

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


@router.get("/presets", response_model=RolePresetsResponse)
async def get_role_presets():
    """Get available role preset configurations."""
    presets = []
    for key, preset in ROLE_PRESETS.items():
        presets.append(
            RolePreset(
                name=key,
                display_name=preset["display_name"],
                player_count=preset["player_count"],
                roles=preset["roles"],
                description=preset.get("description", ""),
            )
        )
    return RolePresetsResponse(presets=presets)


@router.get("/available", response_model=AvailableRolesResponse)
async def get_available_roles():
    """Get all available roles."""
    roles = []
    for name, role_cls in RoleRegistry.all().items():
        roles.append(
            RoleInfo(
                name=role_cls.name,
                display_name=role_cls.display_name,
                faction=role_cls.faction.value if hasattr(role_cls.faction, "value") else str(role_cls.faction),
                has_night_action=role_cls.has_night_action,
                description=f"{role_cls.display_name}（{role_cls.faction.value}阵营）",
            )
        )
    return AvailableRolesResponse(roles=roles)
