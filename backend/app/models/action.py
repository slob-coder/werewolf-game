"""GameAction database model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GameAction(Base):
    """A single action submitted by a player during a game."""

    __tablename__ = "game_actions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    game_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("games.id"), nullable=False, index=True
    )
    player_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("game_players.id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(String(30), nullable=False)
    target_seat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    is_timeout: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    game = relationship("Game", back_populates="actions")
    player = relationship("GamePlayer", lazy="selectin")
