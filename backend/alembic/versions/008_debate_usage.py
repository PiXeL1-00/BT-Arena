"""Add debate_usage table for daily call cap tracking.

Revision ID: 008
Revises: 007_galileo_analytics
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "debate_usage",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("model_key", sa.String(128), nullable=False),
        sa.Column("usage_date", sa.Date, nullable=False),
        sa.Column("call_count", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("model_key", "usage_date", name="uq_debate_usage_model_date"),
        sa.Index("ix_debate_usage_model_date", "model_key", "usage_date"),
    )


def downgrade() -> None:
    op.drop_table("debate_usage")
