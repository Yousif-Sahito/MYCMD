"""Phase 7 synchronization tables."""

import sqlalchemy as sa
from alembic import op

revision = "002_phase7_sync"
down_revision = "001_phase6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_operations",
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False),
        sa.Column("device_id", sa.String(36), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("base_version", sa.Integer(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("owner_id", "operation_id"),
        sa.CheckConstraint(
            "entity_type IN ('projects','skills','education','certificates','milestones')",
            name="ck_sync_operations_kind",
        ),
        sa.CheckConstraint(
            "action IN ('create','update','delete')", name="ck_sync_operations_action"
        ),
    )
    op.create_table(
        "change_log",
        sa.Column("sequence", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tombstone", sa.Boolean(), nullable=False),
        sa.Column("record_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("owner_id", "sequence"),
    )
    op.create_index("ix_change_log_owner_sequence", "change_log", ["owner_id", "sequence"])
    op.create_table(
        "sync_cursor",
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("owner_id"),
    )
    op.create_table(
        "bootstrap_state",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("provisioned", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("INSERT INTO bootstrap_state (id, provisioned) VALUES ('singleton', false)")


def downgrade() -> None:
    op.drop_table("bootstrap_state")
    op.drop_table("sync_cursor")
    op.drop_index("ix_change_log_owner_sequence", table_name="change_log")
    op.drop_table("change_log")
    op.drop_table("sync_operations")
