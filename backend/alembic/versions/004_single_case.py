"""Add case_id to runs and cached_result_sets, drop max_cases from runs.

Revision ID: 004
Revises: 003
Create Date: 2026-02-08 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # runs: add case_id, drop max_cases
    op.add_column(
        "runs",
        sa.Column("case_id", sa.String(128), server_default="", nullable=False),
    )
    op.drop_column("runs", "max_cases")

    # cached_result_sets: add case_id, rebuild constraints
    op.add_column(
        "cached_result_sets",
        sa.Column("case_id", sa.String(128), server_default="", nullable=False),
    )
    # purge stale entries (startup wipe also handles this)
    op.execute("DELETE FROM cached_result_sets")

    op.drop_constraint("uq_cache_slot", "cached_result_sets", type_="unique")
    op.drop_index("ix_cache_dataset_model_exp", "cached_result_sets")

    op.create_unique_constraint(
        "uq_cache_slot",
        "cached_result_sets",
        ["dataset_id", "model_key", "case_id", "slot_number"],
    )
    op.create_index(
        "ix_cache_dataset_model_case_exp",
        "cached_result_sets",
        ["dataset_id", "model_key", "case_id", "expires_at"],
    )


def downgrade() -> None:
    # cached_result_sets: revert
    op.drop_index("ix_cache_dataset_model_case_exp", "cached_result_sets")
    op.drop_constraint("uq_cache_slot", "cached_result_sets", type_="unique")
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
    op.drop_column("cached_result_sets", "case_id")

    # runs: revert
    op.add_column(
        "runs",
        sa.Column("max_cases", sa.Integer(), nullable=True),
    )
    op.drop_column("runs", "case_id")
