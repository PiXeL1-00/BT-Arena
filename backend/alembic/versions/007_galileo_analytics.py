"""Galileo analytics: llm_model + galileo_eval_run + galileo_eval_payload.

Revision ID: 007
Revises: 006
Create Date: 2026-02-10 03:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "llm_model",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_llm_provider_model "
        "ON llm_model (provider, model_name, COALESCE(model_version, ''))"
    )

    op.create_table(
        "galileo_eval_run",
        sa.Column(
            "run_id",
            sa.dialects.postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "llm_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("llm_model.id"),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.Text(), nullable=False),
        sa.Column("dataset_version", sa.Text(), nullable=True),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column(
            "eval_mode",
            sa.Text(),
            server_default=sa.text("'galileo'"),
            nullable=False,
        ),
        sa.Column("score_total", sa.Numeric(), nullable=True),
        sa.Column("score_components", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("failure_flags", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "run_type",
            sa.Text(),
            server_default=sa.text("'user'"),
            nullable=False,
        ),
        sa.Column("benchmark_tag", sa.Text(), nullable=True),
        sa.Column("batch_id", sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column("source_run_id", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("app_version", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("git_sha", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_ger_llm_created",
        "galileo_eval_run",
        [sa.text("llm_id"), sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_ger_runtype_tag",
        "galileo_eval_run",
        [sa.text("run_type"), sa.text("benchmark_tag"), sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_ger_eval_mode",
        "galileo_eval_run",
        [sa.text("eval_mode"), sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_ger_ds_case",
        "galileo_eval_run",
        [sa.text("dataset_id"), sa.text("case_id"), sa.text("created_at DESC")],
    )
    op.execute(
        "CREATE INDEX ix_ger_batch ON galileo_eval_run (batch_id) "
        "WHERE batch_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_idempotency "
        "ON galileo_eval_run (idempotency_key) "
        "WHERE idempotency_key IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_source_run_eval "
        "ON galileo_eval_run (source_run_id, eval_mode) "
        "WHERE source_run_id IS NOT NULL"
    )

    op.create_table(
        "galileo_eval_payload",
        sa.Column(
            "run_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("galileo_eval_run.run_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("result_payload", sa.dialects.postgresql.JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("galileo_eval_payload")
    op.drop_table("galileo_eval_run")
    op.drop_table("llm_model")
