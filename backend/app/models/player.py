"""GamePlayer database model."""

from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GamePlayer(Base):
    """Association between a game and an agent playing in it."""

    __tablename__ = "game_players"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    game_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("games.id"), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("agents.id"), nullable=False
    )
    seat: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    death_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    death_cause: Mapped[str | None] = mapped_column(String(30), nullable=True)
    items: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint("game_id", "seat", name="uq_game_player_seat"),
        UniqueConstraint("game_id", "agent_id", name="uq_game_player_agent"),
    )

    # Relationships
    game = relationship("Game", back_populates="players")
    agent = relationship("Agent", lazy="selectin")
