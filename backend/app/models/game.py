"""Game database model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Game(Base):
    """A single game instance tied to a room."""

    __tablename__ = "games"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    room_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("rooms.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    current_phase: Mapped[str | None] = mapped_column(String(30), nullable=True)
    current_round: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    role_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    winner: Mapped[str | None] = mapped_column(String(20), nullable=True)
    win_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    room = relationship("Room", back_populates="games", lazy="selectin")
    players = relationship("GamePlayer", back_populates="game", lazy="selectin")
    events = relationship("GameEvent", back_populates="game", lazy="selectin")
    actions = relationship("GameAction", back_populates="game", lazy="selectin")
