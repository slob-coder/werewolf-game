"""Pydantic schemas for role configuration endpoints."""

from pydantic import BaseModel


class RoleInfo(BaseModel):
    name: str
    display_name: str
    faction: str
    has_night_action: bool
    description: str = ""


class RolePreset(BaseModel):
    name: str
    display_name: str
    player_count: int
    roles: dict[str, int]
    description: str = ""


class RolePresetsResponse(BaseModel):
    presets: list[RolePreset]


class AvailableRolesResponse(BaseModel):
    roles: list[RoleInfo]
