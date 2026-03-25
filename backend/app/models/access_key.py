"""Access Key model for CLI authentication."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccessKey(Base):
    """Access Key for CLI authentication (long-lived, can be revoked)."""

    __tablename__ = "access_keys"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=True)  # e.g., "CLI", "CI/CD"
    key_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="access_keys", lazy="selectin")
