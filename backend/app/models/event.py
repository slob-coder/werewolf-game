"""GameEvent database model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GameEvent(Base):
    """Timestamped event log for a game."""

    __tablename__ = "game_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    game_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("games.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(String(30), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    visibility: Mapped[str] = mapped_column(String(10), default="public", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_game_events_game_round", "game_id", "round"),
    )

    # Relationships
    game = relationship("Game", back_populates="events")
