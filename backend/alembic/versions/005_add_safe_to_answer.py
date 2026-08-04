"""Add safe_to_answer column to dataset_cases.

Revision ID: 005
Revises: 004
Create Date: 2026-02-08 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "dataset_cases",
        sa.Column("safe_to_answer", sa.Boolean(), server_default="true", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("dataset_cases", "safe_to_answer")
