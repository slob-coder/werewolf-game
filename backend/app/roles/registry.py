"""Role registry — register and instantiate role classes by name."""

from __future__ import annotations

from typing import Type

from app.roles.base import RoleBase


class RoleRegistry:
    """Central registry that maps role names to their classes."""

    _roles: dict[str, Type[RoleBase]] = {}

    @classmethod
    def register(cls, role_class: Type[RoleBase]) -> Type[RoleBase]:
        """Register a role class.  Can be used as a decorator."""
        cls._roles[role_class.name] = role_class
        return role_class

    @classmethod
    def get(cls, name: str) -> Type[RoleBase]:
        """Look up a role class by its canonical name."""
        if name not in cls._roles:
            raise KeyError(f"Unknown role: {name}")
        return cls._roles[name]

    @classmethod
    def create(cls, name: str) -> RoleBase:
        """Create a single role instance."""
        return cls.get(name)()

    @classmethod
    def create_from_config(cls, config: dict[str, int]) -> list[RoleBase]:
        """Create role instances from a ``{"werewolf": 3, ...}`` mapping."""
        roles: list[RoleBase] = []
        for role_name, count in config.items():
            role_cls = cls.get(role_name)
            roles.extend(role_cls() for _ in range(count))
        return roles

    @classmethod
    def all_names(cls) -> list[str]:
        return list(cls._roles.keys())

    @classmethod
    def clear(cls) -> None:
        """Remove all registrations (for testing)."""
        cls._roles.clear()
