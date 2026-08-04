"""Initial schema – all 7 tables.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # datasets
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("meta_json", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # dataset_cases
    op.create_table(
        "dataset_cases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_id",
            sa.String(64),
            sa.ForeignKey("datasets.id"),
            nullable=False,
        ),
        sa.Column("case_id", sa.String(128), nullable=False),
        sa.Column("topic", sa.String(256), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("pressure_score", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(32), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_dataset_cases_dataset_case",
        "dataset_cases",
        ["dataset_id", "case_id"],
    )

    # runs
    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.String(64),
            sa.ForeignKey("datasets.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), server_default="PENDING"),
        sa.Column("models_json", sa.JSON(), nullable=False),
        sa.Column("max_cases", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )

    # run_case_status
    op.create_table(
        "run_case_status",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("runs.run_id"),
            nullable=False,
        ),
        sa.Column("case_id", sa.String(128), nullable=False),
        sa.Column("model_key", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_rcs_run_case_model",
        "run_case_status",
        ["run_id", "case_id", "model_key"],
    )

    # run_messages
    op.create_table(
        "run_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("runs.run_id"),
            nullable=False,
        ),
        sa.Column("case_id", sa.String(128), nullable=False),
        sa.Column("model_key", sa.String(128), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_rm_run_case", "run_messages", ["run_id", "case_id"])

    # run_results
    op.create_table(
        "run_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("runs.run_id"),
            nullable=False,
        ),
        sa.Column("case_id", sa.String(128), nullable=False),
        sa.Column("model_key", sa.String(128), nullable=False),
        sa.Column("verdict", sa.String(32), nullable=False),
        sa.Column("label", sa.String(32), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_used_json", sa.JSON(), nullable=False),
        sa.Column("critical_fail_reason", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cost_estimate", sa.Float(), server_default="0"),
        sa.Column("judge_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_rr_run_model", "run_results", ["run_id", "model_key"])

    # run_events
    op.create_table(
        "run_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("runs.run_id"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_re_run_seq", "run_events", ["run_id", "seq"])


def downgrade() -> None:
    op.drop_table("run_events")
    op.drop_table("run_results")
    op.drop_table("run_messages")
    op.drop_table("run_case_status")
    op.drop_table("runs")
    op.drop_table("dataset_cases")
    op.drop_table("datasets")
