"""
Profile Models
==============
SQLAlchemy ORM models and Pydantic schemas for user health profiles
and assessment history.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session as OrmSession


# ── SQLAlchemy ORM ────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class UserProfileORM(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Demographics
    age = Column(Integer, nullable=True)
    biological_sex = Column(String, nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)

    # Lifestyle
    activity_level = Column(String, nullable=True)   # sedentary|light|moderate|active
    smoking_status = Column(String, nullable=True)   # never|former|current
    diet_quality = Column(String, nullable=True)     # healthy|mixed|poor
    sleep_hours = Column(String, nullable=True)      # under5|5to6|7to8|over8
    alcohol_weekly = Column(String, nullable=True)   # none|light|moderate|heavy
    stress_level = Column(Integer, nullable=True)    # 1–5
    salt_intake = Column(String, nullable=True)      # low|moderate|high
    sugar_intake = Column(String, nullable=True)     # none|occasional|daily|heavy

    # Condition-specific flags
    family_diabetes = Column(Boolean, nullable=True)
    family_cvd = Column(Boolean, nullable=True)
    family_htn = Column(Boolean, nullable=True)
    prediabetes_flag = Column(Boolean, nullable=True)
    symptom_flags_json = Column(Text, nullable=True)   # JSON list

    # Risk history (last known values)
    last_diabetes_risk = Column(Float, nullable=True)
    last_cvd_risk = Column(Float, nullable=True)
    last_htn_risk = Column(Float, nullable=True)
    last_assessment_date = Column(DateTime, nullable=True)
    assessments_completed = Column(Integer, default=0)

    # ChromaDB index reference
    chroma_doc_id = Column(String, nullable=True)


class AssessmentResultORM(Base):
    __tablename__ = "assessment_results"

    result_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=True)
    condition = Column(String, nullable=False)
    risk_probability = Column(Float, nullable=False)
    risk_category = Column(String, nullable=False)
    raw_result_json = Column(Text, nullable=True)
    lifestyle_inputs_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Pydantic Models ───────────────────────────────────────────────────────────

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
        flags = []
        if orm.symptom_flags_json:
            try:
                flags = json.loads(orm.symptom_flags_json)
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
            symptom_flags=flags,
            last_diabetes_risk=orm.last_diabetes_risk,
            last_cvd_risk=orm.last_cvd_risk,
            last_htn_risk=orm.last_htn_risk,
            last_assessment_date=orm.last_assessment_date,
            assessments_completed=orm.assessments_completed or 0,
            chroma_doc_id=orm.chroma_doc_id,
        )

    def to_orm_dict(self) -> Dict[str, Any]:
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
            "symptom_flags_json": json.dumps(self.symptom_flags),
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
