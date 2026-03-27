"""Server Exception database model for tracking backend errors."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ServerException(Base):
    """Server-side exceptions for debugging and monitoring."""

    __tablename__ = "server_exceptions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    
    # Exception info
    exception_type: Mapped[str] = mapped_column(String(200), nullable=False)
    exception_message: Mapped[str] = mapped_column(Text, nullable=False)
    exception_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Request context (if available)
    request_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    request_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Game context (if available)
    room_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    game_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )
    
    # Additional context
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Resolution tracking
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Indexes
    __table_args__ = (
        Index("ix_server_exceptions_type", "exception_type"),
        Index("ix_server_exceptions_timestamp", "created_at"),
        Index("ix_server_exceptions_resolved", "resolved"),
        Index("ix_server_exceptions_room_id", "room_id"),
        Index("ix_server_exceptions_game_id", "game_id"),
    )
