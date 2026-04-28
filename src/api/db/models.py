"""
Unified ORM Models
==================
Single source of truth for the relational schema. Replaces the previous
split between `src/api/db/users_db.py` (raw sqlite3) and
`src/profile/models.py` (separate SQLAlchemy file).

Tables
------
    users                — account credentials + basic demographics
    user_profiles        — health-profile state (1 row per user)
    assessment_results   — every completed assessment (history)
    profile_embeddings   — pgvector row per user (RAG; optional)

All FKs use ON DELETE CASCADE so deleting a `users` row wipes all
dependent rows in one shot.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from src.api.db.database import Base, db_dialect


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.utcnow()


# JSONB on Postgres, JSON (TEXT) on SQLite — same Python interface.
JsonCol = JSON().with_variant(JSONB(), "postgresql")


# ── Users ────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    # Optional profile fields (kept here so the Settings page still works)
    dob: Mapped[str] = mapped_column(String, default="", nullable=False)
    gender: Mapped[str] = mapped_column(String, default="", nullable=False)
    height: Mapped[str] = mapped_column(String, default="", nullable=False)
    weight: Mapped[str] = mapped_column(String, default="", nullable=False)

    created_at: Mapped[str] = mapped_column(String, nullable=False)

    # Cascading children
    profile: Mapped[Optional["UserProfile"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    assessments: Mapped[List["AssessmentResult"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    embedding: Mapped[Optional["ProfileEmbedding"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "password_hash": self.password_hash,
            "dob": self.dob or "",
            "gender": self.gender or "",
            "height": self.height or "",
            "weight": self.weight or "",
            "created_at": self.created_at,
        }


# ── User Profile (health) ────────────────────────────────────────────────────
class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    # Demographics
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    biological_sex: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bmi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Lifestyle
    activity_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    smoking_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    diet_quality: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sleep_hours: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    alcohol_weekly: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stress_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salt_intake: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sugar_intake: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Family / condition flags
    family_diabetes: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    family_cvd: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    family_htn: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    prediabetes_flag: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # JSON list of free-text symptoms — JSONB on Postgres
    symptom_flags = mapped_column(JsonCol, nullable=True)

    # Risk history (last known values)
    last_diabetes_risk: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_cvd_risk: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_htn_risk: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_assessment_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    assessments_completed: Mapped[int] = mapped_column(Integer, default=0)

    # Pointer to the embedding row (denormalised so existing code that
    # tracks `chroma_doc_id` keeps working).
    chroma_doc_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")


# ── Assessment Results ───────────────────────────────────────────────────────
class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    result_id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    condition: Mapped[str] = mapped_column(String, nullable=False)
    risk_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_category: Mapped[str] = mapped_column(String, nullable=False)

    # JSON blobs — full result + lifestyle inputs
    raw_result = mapped_column(JsonCol, nullable=True)
    lifestyle_inputs = mapped_column(JsonCol, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="assessments")


# ── Profile Embedding (pgvector) ─────────────────────────────────────────────
# Defined dynamically so we don't import the `pgvector` SQLAlchemy type when
# running on SQLite (CI / local dev fallback). On SQLite we store the raw
# floats as a JSON list — the table is dormant anyway because RAG is disabled
# in the production singleton.
class ProfileEmbedding(Base):
    __tablename__ = "profile_embeddings"

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    # Embedding column — vector(384) on Postgres, JSON list elsewhere.
    if db_dialect() == "postgresql":
        from pgvector.sqlalchemy import Vector  # imported lazily

        embedding = mapped_column(Vector(384), nullable=True)
    else:
        embedding = mapped_column(JsonCol, nullable=True)

    user: Mapped["User"] = relationship(back_populates="embedding")
