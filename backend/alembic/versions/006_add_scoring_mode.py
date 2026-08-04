"""Add scoring_mode column to runs table.

Tracks whether a run used deterministic (keyword-only) or ML-enhanced
scoring so that ``compare_runs`` can warn when modes differ.

Revision ID: 006
Revises: 005
Create Date: 2026-02-08 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "scoring_mode",
            sa.String(32),
            server_default="deterministic",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("runs", "scoring_mode")
