"""Baseline schema — users, user_profiles, assessment_results, profile_embeddings.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-04-24 00:00:00 UTC

This is the Tier 2 baseline: it consolidates what was previously
spread across two SQLite files (data/users.db + data/profiles/profiles.db)
into a single Postgres database. ON DELETE CASCADE foreign keys mean
deleting a user wipes their profile, history, and embedding in one shot.

The pgvector extension is created in env.py before this migration runs
(skipped on SQLite — `embedding` falls back to a JSON column there).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_col() -> sa.types.TypeEngine:
    """JSONB on Postgres, JSON elsewhere — same Python interface."""
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("dob", sa.String(), nullable=False, server_default=""),
        sa.Column("gender", sa.String(), nullable=False, server_default=""),
        sa.Column("height", sa.String(), nullable=False, server_default=""),
        sa.Column("weight", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── user_profiles ────────────────────────────────────────────────────────
    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("biological_sex", sa.String(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("bmi", sa.Float(), nullable=True),
        sa.Column("activity_level", sa.String(), nullable=True),
        sa.Column("smoking_status", sa.String(), nullable=True),
        sa.Column("diet_quality", sa.String(), nullable=True),
        sa.Column("sleep_hours", sa.String(), nullable=True),
        sa.Column("alcohol_weekly", sa.String(), nullable=True),
        sa.Column("stress_level", sa.Integer(), nullable=True),
        sa.Column("salt_intake", sa.String(), nullable=True),
        sa.Column("sugar_intake", sa.String(), nullable=True),
        sa.Column("family_diabetes", sa.Boolean(), nullable=True),
        sa.Column("family_cvd", sa.Boolean(), nullable=True),
        sa.Column("family_htn", sa.Boolean(), nullable=True),
        sa.Column("prediabetes_flag", sa.Boolean(), nullable=True),
        sa.Column("symptom_flags", _json_col(), nullable=True),
        sa.Column("last_diabetes_risk", sa.Float(), nullable=True),
        sa.Column("last_cvd_risk", sa.Float(), nullable=True),
        sa.Column("last_htn_risk", sa.Float(), nullable=True),
        sa.Column("last_assessment_date", sa.DateTime(), nullable=True),
        sa.Column("assessments_completed", sa.Integer(), server_default="0"),
        sa.Column("chroma_doc_id", sa.String(), nullable=True),
    )

    # ── assessment_results ───────────────────────────────────────────────────
    op.create_table(
        "assessment_results",
        sa.Column("result_id", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("condition", sa.String(), nullable=False),
        sa.Column("risk_probability", sa.Float(), nullable=False),
        sa.Column("risk_category", sa.String(), nullable=False),
        sa.Column("raw_result", _json_col(), nullable=True),
        sa.Column("lifestyle_inputs", _json_col(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_assessment_results_user_id", "assessment_results", ["user_id"]
    )
    op.create_index(
        "ix_assessment_results_created_at", "assessment_results", ["created_at"]
    )

    # ── profile_embeddings ───────────────────────────────────────────────────
    if is_pg:
        # pgvector type — extension is created in env.py before migrations run.
        from pgvector.sqlalchemy import Vector

        op.create_table(
            "profile_embeddings",
            sa.Column(
                "user_id",
                sa.String(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("document", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("embedding", Vector(384), nullable=True),
        )
    else:
        op.create_table(
            "profile_embeddings",
            sa.Column(
                "user_id",
                sa.String(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("document", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("embedding", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("profile_embeddings")
    op.drop_index("ix_assessment_results_created_at", table_name="assessment_results")
    op.drop_index("ix_assessment_results_user_id", table_name="assessment_results")
    op.drop_table("assessment_results")
    op.drop_table("user_profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
