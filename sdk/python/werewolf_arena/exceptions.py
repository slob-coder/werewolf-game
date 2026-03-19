"""Custom exception types for the Werewolf Arena SDK."""

from __future__ import annotations


class ArenaError(Exception):
    """Base exception for all Werewolf Arena SDK errors."""
    pass


class ArenaConnectionError(ArenaError):
    """Raised when a Socket.IO or HTTP connection fails."""
    pass


class ArenaAPIError(ArenaError):
    """Raised when the REST API returns an error response."""
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


class ArenaTimeoutError(ArenaError):
    """Raised when an operation times out."""
    pass


class ArenaAuthError(ArenaError):
    """Raised when authentication fails."""
    pass
