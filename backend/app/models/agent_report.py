"""Agent Report database model for observability."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AgentReport(Base):
    """Agent observability reports: exceptions, events, health status."""

    __tablename__ = "agent_reports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("agents.id"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # exception | event | health
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Session context
    room_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    game_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )

    # Report content (JSON)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    agent = relationship("Agent", back_populates="reports")

    # Indexes
    __table_args__ = (
        Index("ix_agent_reports_agent_id", "agent_id"),
        Index("ix_agent_reports_timestamp", "timestamp"),
        Index("ix_agent_reports_type", "report_type"),
        Index("ix_agent_reports_room_id", "room_id"),
        Index("ix_agent_reports_game_id", "game_id"),
    )
