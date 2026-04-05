"""
Profile Store
=============
SQLite-backed CRUD for user profiles and assessment history.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.profile.models import (
    Base, UserProfileORM, AssessmentResultORM, UserProfile, AssessmentResult
)

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "profiles" / "profiles.db"


class ProfileStore:
    def __init__(self, db_url: Optional[str] = None):
        url = db_url or f"sqlite:///{_DEFAULT_DB_PATH}"
        _DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)

    # ── User Profile CRUD ─────────────────────────────────────────────────────

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        with Session(self.engine) as session:
            orm = session.get(UserProfileORM, user_id)
            if not orm:
                return None
            return UserProfile.from_orm_model(orm)

    def upsert_profile(self, profile: UserProfile) -> UserProfile:
        with Session(self.engine) as session:
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
        with Session(self.engine) as session:
            orm = session.get(UserProfileORM, user_id)
            if not orm:
                return False
            session.delete(orm)
            session.commit()
            return True

    # ── Assessment History ────────────────────────────────────────────────────

    def save_assessment(self, result: AssessmentResult) -> AssessmentResult:
        with Session(self.engine) as session:
            orm = AssessmentResultORM(
                result_id=result.result_id,
                user_id=result.user_id,
                session_id=result.session_id,
                condition=result.condition,
                risk_probability=result.risk_probability,
                risk_category=result.risk_category,
                raw_result_json=json.dumps(result.raw_result) if result.raw_result else None,
                lifestyle_inputs_json=json.dumps(result.lifestyle_inputs) if result.lifestyle_inputs else None,
                created_at=result.created_at,
            )
            session.add(orm)
            session.commit()
        return result

    def get_assessment_history(
        self, user_id: str, limit: int = 10
    ) -> List[AssessmentResult]:
        with Session(self.engine) as session:
            rows = (
                session.query(AssessmentResultORM)
                .filter_by(user_id=user_id)
                .order_by(AssessmentResultORM.created_at.desc())
                .limit(limit)
                .all()
            )
            results = []
            for r in rows:
                results.append(AssessmentResult(
                    result_id=r.result_id,
                    user_id=r.user_id,
                    session_id=r.session_id,
                    condition=r.condition,
                    risk_probability=r.risk_probability,
                    risk_category=r.risk_category,
                    raw_result=json.loads(r.raw_result_json) if r.raw_result_json else None,
                    lifestyle_inputs=json.loads(r.lifestyle_inputs_json) if r.lifestyle_inputs_json else None,
                    created_at=r.created_at,
                ))
            return results
