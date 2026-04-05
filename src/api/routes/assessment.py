"""
Structured Assessment Routes
=============================
Accepts a complete lifestyle questionnaire payload and runs a full
risk assessment — used by the Assessment Wizard in the frontend.

POST /api/v1/assessment          — run full lifestyle-based assessment
GET  /api/v1/assessment/questions/{condition}  — fetch question bank for wizard
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/assessment", tags=["Assessment"])
logger = logging.getLogger(__name__)


# ── Request / Response Schemas ────────────────────────────────────────────────

class LifestyleAnswers(BaseModel):
    """Lifestyle consultation answers from the wizard."""
    # Demographics
    age: Optional[int] = Field(None, ge=18, le=120)
    biological_sex: Optional[str] = None       # "male" | "female" (from wizard)
    gender: Optional[str] = None               # "male" | "female" (alias from chat/direct)
    height_cm: Optional[float] = Field(None, ge=50, le=250)
    weight_kg: Optional[float] = Field(None, ge=20, le=500)

    # Shared lifestyle
    activity_level: Optional[str] = None       # sedentary|light|moderate|active
    smoking_status: Optional[str] = None       # never|former|current
    diet_quality: Optional[str] = None         # healthy|mixed|poor
    sleep_hours: Optional[str] = None          # under5|5to6|7to8|over8
    alcohol_weekly: Optional[str] = None       # none|light|moderate|heavy
    stress_level: Optional[int] = Field(None, ge=1, le=5)
    salt_intake: Optional[str] = None          # low|moderate|high
    sugar_intake: Optional[str] = None         # none|occasional|daily|heavy

    # Condition-specific
    family_diabetes: Optional[bool] = None
    family_cvd: Optional[bool] = None
    family_htn: Optional[bool] = None
    prediabetes_flag: Optional[bool] = None
    diabetes: Optional[bool] = None
    self_reported_hbp: Optional[str] = None    # yes|no|unknown
    self_reported_hchol: Optional[str] = None  # yes|no|unknown
    cardiac_symptoms: Optional[bool] = None
    diabetes_symptoms: Optional[bool] = None

    # Optional clinical values (overrides lifestyle estimates if provided)
    hba1c: Optional[float] = Field(None, ge=3.0, le=20.0)
    fasting_glucose: Optional[float] = Field(None, ge=50.0, le=600.0)
    total_cholesterol: Optional[float] = Field(None, ge=50.0, le=600.0)
    hdl_cholesterol: Optional[float] = Field(None, ge=10.0, le=150.0)
    systolic_bp: Optional[float] = Field(None, ge=60.0, le=300.0)
    bmi: Optional[float] = Field(None, ge=10.0, le=80.0)
    waist_circumference: Optional[float] = Field(None, ge=40.0, le=250.0)


class AssessmentRequest(BaseModel):
    condition: str = Field(..., description="diabetes | cvd | hypertension")
    answers: LifestyleAnswers
    user_id: Optional[str] = Field(None, description="Stable user UUID for profile persistence")
    session_id: Optional[str] = None
    include_explanation: bool = True
    include_recommendations: bool = True


class AssessmentResponse(BaseModel):
    success: bool
    condition: str
    risk: Dict[str, Any]
    explanation: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[Dict[str, Any]]] = None
    lifestyle_features_used: Dict[str, Any] = Field(
        default_factory=dict,
        description="Feature values actually passed to the model (shows what was estimated vs. provided)"
    )
    profile_updated: bool = False


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=AssessmentResponse)
async def run_assessment(request: AssessmentRequest):
    """
    Run a full lifestyle-based risk assessment.

    Accepts plain lifestyle answers (no lab values needed), maps them to
    model features, and returns a risk score with explanation and
    personalised recommendations.
    """
    condition = request.condition.lower()
    if condition not in ("diabetes", "cvd", "hypertension"):
        raise HTTPException(
            status_code=422,
            detail="condition must be one of: diabetes, cvd, hypertension",
        )

    try:
        from src.lifestyle.feature_mapper import lifestyle_mapper
        from src.profile.profile_service import profile_service

        # Build answers dict (drop None values)
        raw_answers = request.answers.model_dump(exclude_none=True)
        # Normalise biological_sex → gender (model expects "gender")
        # Accept either field name; gender takes priority
        if "biological_sex" in raw_answers and "gender" not in raw_answers:
            raw_answers["gender"] = raw_answers.pop("biological_sex")
        elif "biological_sex" in raw_answers:
            raw_answers.pop("biological_sex")

        # Load profile for skip-logic and BMI inheritance
        profile = None
        if request.user_id:
            profile = profile_service.get_profile(request.user_id)

        # Map lifestyle → model features
        if condition == "diabetes":
            features = lifestyle_mapper.map_for_diabetes(raw_answers, profile)
        elif condition == "cvd":
            features = lifestyle_mapper.map_for_cvd(raw_answers, profile)
        else:
            features = lifestyle_mapper.map_for_hypertension(raw_answers, profile)

        # Run prediction
        result = _call_prediction_service(
            condition, features,
            include_explanation=request.include_explanation,
            include_recommendations=request.include_recommendations,
        )

        # Persist profile + result for logged-in users
        profile_updated = False
        if request.user_id:
            try:
                profile_service.update_profile_from_answers(request.user_id, raw_answers)
                profile_service.update_profile_from_result(request.user_id, condition, result)
                profile_service.save_assessment(
                    request.user_id, request.session_id, condition, raw_answers, result
                )
                profile_updated = True
            except Exception as e:
                logger.warning("Profile update failed: %s", e)

        return AssessmentResponse(
            success=True,
            condition=condition,
            risk=result.get("risk", {}),
            explanation=result.get("explanation"),
            recommendations=result.get("recommendations"),
            lifestyle_features_used=features,
            profile_updated=profile_updated,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Assessment failed for %s: %s", condition, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")


@router.get("/questions/{condition}")
async def get_questions(condition: str):
    """
    Return the question bank for a given condition.
    Used by the frontend Assessment Wizard to render step-by-step questions.
    """
    condition = condition.lower()
    if condition not in ("diabetes", "cvd", "hypertension"):
        raise HTTPException(
            status_code=422,
            detail="condition must be one of: diabetes, cvd, hypertension",
        )

    from src.chatbot.questions.question_bank import CONDITION_QUESTIONS
    from src.chatbot.questions.question_flow import QuestionFlow

    flow = QuestionFlow()
    steps = flow.get_wizard_steps(condition)

    return {
        "condition": condition,
        "steps": [
            [
                {
                    "id": q.id,
                    "text": q.text,
                    "response_type": q.response_type,
                    "options": q.options,
                    "option_keys": q.option_keys,
                    "maps_to": q.maps_to,
                    "required": q.required,
                    "unit_hint": q.unit_hint,
                    "layer": q.layer,
                }
                for q in step
            ]
            for step in steps
        ],
    }


# ── Prediction helper ─────────────────────────────────────────────────────────

def _call_prediction_service(
    condition: str,
    features: Dict[str, Any],
    include_explanation: bool = True,
    include_recommendations: bool = True,
) -> Dict[str, Any]:
    if condition == "diabetes":
        from src.api.services.prediction_service import prediction_service
        result = prediction_service.predict(features, include_explanation=include_explanation)
        if include_recommendations:
            result["recommendations"] = prediction_service.generate_recommendations(features, result)
        return result

    if condition == "cvd":
        from src.api.services.cvd_prediction_service import cvd_prediction_service
        result = cvd_prediction_service.predict(features, include_explanation=include_explanation)
        if include_recommendations:
            result["recommendations"] = cvd_prediction_service.generate_recommendations(features, result)
        return result

    if condition == "hypertension":
        from src.api.services.hypertension_prediction_service import hypertension_prediction_service
        result = hypertension_prediction_service.predict(features, include_explanation=include_explanation)
        if include_recommendations:
            result["recommendations"] = hypertension_prediction_service.generate_recommendations(features, result)
        return result

    raise ValueError(f"Unknown condition: {condition}")
