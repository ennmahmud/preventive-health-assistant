"""
Profile Models (Pydantic)
=========================
Pydantic schemas for user health profiles and assessment history.

The ORM half lives in `src/api/db/models.py` — this module re-exports
those classes under their old names so existing imports keep working:

    from src.profile.models import (
        Base, UserProfileORM, AssessmentResultORM,
        UserProfile, AssessmentResult,
    )
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ── Re-export ORM classes under their legacy names ───────────────────────────
from src.api.db.database import Base  # noqa: F401
from src.api.db.models import UserProfile as UserProfileORM  # noqa: F401
from src.api.db.models import AssessmentResult as AssessmentResultORM  # noqa: F401


# ── Pydantic Models ──────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Demographics
    age: Optional[int] = None
    biological_sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None

    # Lifestyle
    activity_level: Optional[str] = None
    smoking_status: Optional[str] = None
    diet_quality: Optional[str] = None
    sleep_hours: Optional[str] = None
    alcohol_weekly: Optional[str] = None
    stress_level: Optional[int] = None
    salt_intake: Optional[str] = None
    sugar_intake: Optional[str] = None

    # Condition flags
    family_diabetes: Optional[bool] = None
    family_cvd: Optional[bool] = None
    family_htn: Optional[bool] = None
    prediabetes_flag: Optional[bool] = None
    symptom_flags: List[str] = Field(default_factory=list)

    # Risk history
    last_diabetes_risk: Optional[float] = None
    last_cvd_risk: Optional[float] = None
    last_htn_risk: Optional[float] = None
    last_assessment_date: Optional[datetime] = None
    assessments_completed: int = 0

    chroma_doc_id: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, orm: UserProfileORM) -> "UserProfile":
        # symptom_flags is a JSON column (JSONB on Postgres). Defensively
        # coerce in case the DB returns None or a stringified blob.
        flags = orm.symptom_flags or []
        if isinstance(flags, str):
            import json
            try:
                flags = json.loads(flags)
            except Exception:
                flags = []

        return cls(
            user_id=orm.user_id,
            created_at=orm.created_at or datetime.utcnow(),
            updated_at=orm.updated_at or datetime.utcnow(),
            age=orm.age,
            biological_sex=orm.biological_sex,
            height_cm=orm.height_cm,
            weight_kg=orm.weight_kg,
            bmi=orm.bmi,
            activity_level=orm.activity_level,
            smoking_status=orm.smoking_status,
            diet_quality=orm.diet_quality,
            sleep_hours=orm.sleep_hours,
            alcohol_weekly=orm.alcohol_weekly,
            stress_level=orm.stress_level,
            salt_intake=orm.salt_intake,
            sugar_intake=orm.sugar_intake,
            family_diabetes=orm.family_diabetes,
            family_cvd=orm.family_cvd,
            family_htn=orm.family_htn,
            prediabetes_flag=orm.prediabetes_flag,
            symptom_flags=list(flags) if flags else [],
            last_diabetes_risk=orm.last_diabetes_risk,
            last_cvd_risk=orm.last_cvd_risk,
            last_htn_risk=orm.last_htn_risk,
            last_assessment_date=orm.last_assessment_date,
            assessments_completed=orm.assessments_completed or 0,
            chroma_doc_id=orm.chroma_doc_id,
        )

    def to_orm_dict(self) -> Dict[str, Any]:
        """
        Returns a dict suitable for setattr-ing onto a UserProfileORM.
        `symptom_flags` is a real JSON column now — pass the raw list.
        """
        return {
            "user_id": self.user_id,
            "updated_at": datetime.utcnow(),
            "age": self.age,
            "biological_sex": self.biological_sex,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "bmi": self.bmi,
            "activity_level": self.activity_level,
            "smoking_status": self.smoking_status,
            "diet_quality": self.diet_quality,
            "sleep_hours": self.sleep_hours,
            "alcohol_weekly": self.alcohol_weekly,
            "stress_level": self.stress_level,
            "salt_intake": self.salt_intake,
            "sugar_intake": self.sugar_intake,
            "family_diabetes": self.family_diabetes,
            "family_cvd": self.family_cvd,
            "family_htn": self.family_htn,
            "prediabetes_flag": self.prediabetes_flag,
            "symptom_flags": list(self.symptom_flags or []),
            "last_diabetes_risk": self.last_diabetes_risk,
            "last_cvd_risk": self.last_cvd_risk,
            "last_htn_risk": self.last_htn_risk,
            "last_assessment_date": self.last_assessment_date,
            "assessments_completed": self.assessments_completed,
            "chroma_doc_id": self.chroma_doc_id,
        }


class AssessmentResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: Optional[str] = None
    condition: str
    risk_probability: float
    risk_category: str
    raw_result: Optional[Dict[str, Any]] = None
    lifestyle_inputs: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
