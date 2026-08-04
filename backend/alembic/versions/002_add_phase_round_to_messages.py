"""Add phase and round columns to run_messages.

Revision ID: 002
Revises: 001
Create Date: 2026-02-07 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "run_messages",
        sa.Column("phase", sa.String(32), nullable=True),
    )
    op.add_column(
        "run_messages",
        sa.Column("round", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("run_messages", "round")
    op.drop_column("run_messages", "phase")
