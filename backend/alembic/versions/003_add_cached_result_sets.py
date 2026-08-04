"""Add cached_result_sets table.

Revision ID: 003
Revises: 002
Create Date: 2026-02-08 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cached_result_sets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_id",
            sa.String(64),
            sa.ForeignKey("datasets.id"),
            nullable=False,
        ),
        sa.Column("model_key", sa.String(128), nullable=False),
        sa.Column("slot_number", sa.Integer(), nullable=False),
        sa.Column(
            "source_run_id",
            sa.String(64),
            sa.ForeignKey("runs.run_id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_served_at", sa.DateTime(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_cache_slot",
        "cached_result_sets",
        ["dataset_id", "model_key", "slot_number"],
    )
    op.create_index(
        "ix_cache_dataset_model_exp",
        "cached_result_sets",
        ["dataset_id", "model_key", "expires_at"],
    )


def downgrade() -> None:
    op.drop_table("cached_result_sets")
