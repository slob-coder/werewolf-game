"""add server_exceptions table for error tracking

Revision ID: 004_server_exceptions
Revises: 003_agent_reports
Create Date: 2026-03-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_server_exceptions"
down_revision: Union[str, None] = "003_agent_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create server_exceptions table."""
    op.create_table(
        "server_exceptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
        ),
        # Exception info
        sa.Column(
            "exception_type",
            sa.String(200),
            nullable=False,
        ),
        sa.Column(
            "exception_message",
            sa.Text,
            nullable=False,
        ),
        sa.Column(
            "exception_traceback",
            sa.Text,
            nullable=True,
        ),
        # Request context
        sa.Column(
            "request_path",
            sa.String(500),
            nullable=True,
        ),
        sa.Column(
            "request_method",
            sa.String(10),
            nullable=True,
        ),
        sa.Column(
            "request_params",
            postgresql.JSON,
            nullable=True,
        ),
        # Game context
        sa.Column(
            "room_id",
            sa.String(100),
            nullable=True,
        ),
        sa.Column(
            "game_id",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
        # Additional context
        sa.Column(
            "context",
            postgresql.JSON,
            nullable=True,
        ),
        # Resolution tracking
        sa.Column(
            "resolved",
            sa.Boolean,
            default=False,
            nullable=False,
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime,
            nullable=True,
        ),
        sa.Column(
            "resolved_by",
            sa.String(100),
            nullable=True,
        ),
        sa.Column(
            "resolution_note",
            sa.Text,
            nullable=True,
        ),
        # Metadata
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes
    op.create_index("ix_server_exceptions_type", "server_exceptions", ["exception_type"])
    op.create_index("ix_server_exceptions_timestamp", "server_exceptions", ["created_at"])
    op.create_index("ix_server_exceptions_resolved", "server_exceptions", ["resolved"])
    op.create_index("ix_server_exceptions_room_id", "server_exceptions", ["room_id"])
    op.create_index("ix_server_exceptions_game_id", "server_exceptions", ["game_id"])


def downgrade() -> None:
    """Drop server_exceptions table."""
    op.drop_index("ix_server_exceptions_game_id", table_name="server_exceptions")
    op.drop_index("ix_server_exceptions_room_id", table_name="server_exceptions")
    op.drop_index("ix_server_exceptions_resolved", table_name="server_exceptions")
    op.drop_index("ix_server_exceptions_timestamp", table_name="server_exceptions")
    op.drop_index("ix_server_exceptions_type", table_name="server_exceptions")
    op.drop_table("server_exceptions")
