"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-03-19 12:50:00.000000+08:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(200), unique=True, nullable=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # ── agents ─────────────────────────────────────────────────
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("api_key_hash", sa.String(256), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("games_won", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    # ── rooms ──────────────────────────────────────────────────
    op.create_table(
        "rooms",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("config", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── games ──────────────────────────────────────────────────
    op.create_table(
        "games",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "room_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("rooms.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("current_phase", sa.String(30), nullable=True),
        sa.Column("current_round", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "role_config", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("winner", sa.String(20), nullable=True),
        sa.Column("win_reason", sa.Text(), nullable=True),
    )

    # ── game_players ───────────────────────────────────────────
    op.create_table(
        "game_players",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "game_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("games.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("agents.id"),
            nullable=False,
        ),
        sa.Column("seat", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("is_alive", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("death_round", sa.Integer(), nullable=True),
        sa.Column("death_cause", sa.String(30), nullable=True),
        sa.Column("items", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.UniqueConstraint("game_id", "seat", name="uq_game_player_seat"),
        sa.UniqueConstraint("game_id", "agent_id", name="uq_game_player_agent"),
    )

    # ── game_events ────────────────────────────────────────────
    op.create_table(
        "game_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "game_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("games.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(30), nullable=False),
        sa.Column("data", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("visibility", sa.String(10), nullable=False, server_default="public"),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_game_events_game_round", "game_events", ["game_id", "round"])

    # ── game_actions ───────────────────────────────────────────
    op.create_table(
        "game_actions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "game_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("games.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "player_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("game_players.id"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(30), nullable=False),
        sa.Column("target_seat", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("is_timeout", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_table("game_actions")
    op.drop_index("idx_game_events_game_round", table_name="game_events")
    op.drop_table("game_events")
    op.drop_table("game_players")
    op.drop_table("games")
    op.drop_table("rooms")
    op.drop_table("agents")
    op.drop_table("users")
