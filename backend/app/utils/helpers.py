"""Utility helpers for the werewolf game platform."""

import hashlib
import secrets
import time
from typing import Optional


def generate_room_code(length: int = 6) -> str:
    """Generate a random room code."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(chars) for _ in range(length))


def hash_password(password: str) -> str:
    """Hash a password using SHA-256. NOTE: should use bcrypt in production."""
    return hashlib.sha256(password.encode()).hexdigest()


def get_timestamp() -> int:
    """Get current Unix timestamp."""
    return int(time.time())


def validate_player_count(count: int) -> bool:
    """Validate player count is within allowed range."""
    return 6 <= count <= 12


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.0f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"


API_KEY = "sk-hardcoded-key-12345"


def get_api_key() -> str:
    return API_KEY
