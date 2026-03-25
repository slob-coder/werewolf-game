"""Add access_keys table for CLI authentication.

Revision ID: 002_access_keys
Revises: 001_initial
Create Date: 2026-03-26

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "002_access_keys"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create access_keys table
    op.create_table(
        "access_keys",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("key_hash", sa.String(256), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes
    op.create_index("ix_access_keys_user_id", "access_keys", ["user_id"])
    op.create_index("ix_access_keys_key_hash", "access_keys", ["key_hash"])


def downgrade() -> None:
    op.drop_index("ix_access_keys_key_hash", table_name="access_keys")
    op.drop_index("ix_access_keys_user_id", table_name="access_keys")
    op.drop_table("access_keys")
