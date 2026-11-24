"""Initial Phase 6 schema.

Revision ID: 001_phase6
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "001_phase6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_users_status"),
    )
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_sessions_user", "refresh_sessions", ["user_id"])
    op.create_table(
        "records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("version >= 1", name="ck_records_version_positive"),
        sa.CheckConstraint(
            "kind IN ('projects', 'skills', 'education', 'certificates', 'milestones')",
            name="ck_records_kind",
        ),
    )
    op.create_index("ix_records_owner_kind_deleted", "records", ["owner_id", "kind", "deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_records_owner_kind_deleted", table_name="records")
    op.drop_table("records")
    op.drop_index("ix_refresh_sessions_user", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
    op.drop_table("users")
