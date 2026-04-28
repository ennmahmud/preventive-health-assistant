"""
Profile Store
=============
SQLAlchemy-backed CRUD for user profiles and assessment history.

Uses the shared engine from `src.api.db.database` so user accounts,
profiles, assessments, and embeddings all live in the same database.
JSON blobs (raw_result, lifestyle_inputs, symptom_flags) are stored
in JSONB columns on Postgres for indexable querying.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.api.db.database import SessionLocal, engine
from src.profile.models import (
    AssessmentResult,
    AssessmentResultORM,
    UserProfile,
    UserProfileORM,
)

logger = logging.getLogger(__name__)


class ProfileStore:
    """
    Backwards-compatible wrapper. The `db_url` argument is accepted but
    ignored — the shared engine in `src.api.db.database` is the single
    source of truth.
    """

    def __init__(self, db_url: Optional[str] = None):
        if db_url:
            logger.warning(
                "ProfileStore: db_url=%s ignored — using shared engine (%s)",
                db_url, engine.url,
            )
        self.engine = engine

    # ── User Profile CRUD ─────────────────────────────────────────────────────

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        with SessionLocal() as session:
            orm = session.get(UserProfileORM, user_id)
            if not orm:
                return None
            return UserProfile.from_orm_model(orm)

    def upsert_profile(self, profile: UserProfile) -> UserProfile:
        with SessionLocal() as session:
            existing = session.get(UserProfileORM, profile.user_id)
            data = profile.to_orm_dict()
            if existing:
                for k, v in data.items():
                    if k != "user_id" and v is not None:
                        setattr(existing, k, v)
            else:
                data["created_at"] = profile.created_at
                new_orm = UserProfileORM(**data)
                session.add(new_orm)
            session.commit()
        return self.get_profile(profile.user_id)

    def delete_profile(self, user_id: str) -> bool:
        with SessionLocal() as session:
            orm = session.get(UserProfileORM, user_id)
            if not orm:
                return False
            session.delete(orm)
            session.commit()
            return True

    # ── Assessment History ────────────────────────────────────────────────────

    def save_assessment(self, result: AssessmentResult) -> AssessmentResult:
        with SessionLocal() as session:
            orm = AssessmentResultORM(
                result_id=result.result_id,
                user_id=result.user_id,
                session_id=result.session_id,
                condition=result.condition,
                risk_probability=result.risk_probability,
                risk_category=result.risk_category,
                raw_result=result.raw_result,           # JSONB on Postgres
                lifestyle_inputs=result.lifestyle_inputs,
                created_at=result.created_at,
            )
            session.add(orm)
            session.commit()
        return result

    def get_assessment_history(
        self, user_id: str, limit: int = 10
    ) -> List[AssessmentResult]:
        with SessionLocal() as session:
            rows = (
                session.query(AssessmentResultORM)
                .filter_by(user_id=user_id)
                .order_by(AssessmentResultORM.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                AssessmentResult(
                    result_id=r.result_id,
                    user_id=r.user_id,
                    session_id=r.session_id,
                    condition=r.condition,
                    risk_probability=r.risk_probability,
                    risk_category=r.risk_category,
                    raw_result=r.raw_result,
                    lifestyle_inputs=r.lifestyle_inputs,
                    created_at=r.created_at,
                )
                for r in rows
            ]
