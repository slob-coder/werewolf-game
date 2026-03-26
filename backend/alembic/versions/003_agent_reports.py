"""add agent_reports table for observability

Revision ID: 003_agent_reports
Revises: 002_access_keys
Create Date: 2026-03-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_agent_reports"
down_revision: Union[str, None] = "002_access_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agent_reports table."""
    op.create_table(
        "agent_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime,
            nullable=False,
        ),
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
        sa.Column(
            "payload",
            postgresql.JSON,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes
    op.create_index("ix_agent_reports_agent_id", "agent_reports", ["agent_id"])
    op.create_index("ix_agent_reports_timestamp", "agent_reports", ["timestamp"])
    op.create_index("ix_agent_reports_type", "agent_reports", ["report_type"])
    op.create_index("ix_agent_reports_room_id", "agent_reports", ["room_id"])
    op.create_index("ix_agent_reports_game_id", "agent_reports", ["game_id"])


def downgrade() -> None:
    """Drop agent_reports table."""
    op.drop_index("ix_agent_reports_game_id", table_name="agent_reports")
    op.drop_index("ix_agent_reports_room_id", table_name="agent_reports")
    op.drop_index("ix_agent_reports_type", table_name="agent_reports")
    op.drop_index("ix_agent_reports_timestamp", table_name="agent_reports")
    op.drop_index("ix_agent_reports_agent_id", table_name="agent_reports")
    op.drop_table("agent_reports")
