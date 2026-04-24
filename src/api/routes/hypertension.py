"""
Hypertension Assessment Routes
================================
API endpoints for hypertension risk assessments.

Endpoints:
  POST /api/v1/health/hypertension/assess         — full assessment
  POST /api/v1/health/hypertension/quick-check    — minimal-input screening
  GET  /api/v1/health/hypertension/model-info     — loaded model metadata
  GET  /api/v1/health/hypertension/features       — feature catalogue

Note: Blood pressure readings are NOT accepted as inputs. The model predicts
BP risk from lifestyle/demographic factors for preventive screening.
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.auth import require_api_key

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.api.schemas.health import RiskCategory, RiskFactor, RiskExplanation, HealthRecommendation
from src.api.schemas.hypertension import (
    HypertensionMetricsInput,
    HypertensionAssessmentRequest,
    HypertensionAssessmentResponse,
    HypertensionRiskResult,
    HypertensionModelInfoResponse,
)
from src.api.services.hypertension_prediction_service import hypertension_prediction_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/health/hypertension",
    tags=["Hypertension Assessments"],
    dependencies=[Depends(require_api_key)],
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _explanation_summary(
    risk_factors: List[RiskFactor], protective_factors: List[RiskFactor]
) -> str:
    parts = []
    if risk_factors:
        names = [rf.factor for rf in risk_factors[:3]]
        parts.append(f"Key factors increasing your hypertension risk: {', '.join(names)}")
    if protective_factors:
        names = [pf.factor for pf in protective_factors[:3]]
        parts.append(f"Factors working in your favour: {', '.join(names)}")
    return (". ".join(parts) + ".") if parts else (
        "Your hypertension risk assessment is based on a combination of health metrics."
    )


def _risk_message(category: str) -> str:
    return {
        "Low":       "Your hypertension risk appears low. Maintain a healthy lifestyle.",
        "Moderate":  "You have some hypertension risk factors. Consider lifestyle changes.",
        "High":      "Your hypertension risk is elevated. Get your blood pressure checked.",
        "Very High": "Your hypertension risk is significantly elevated. Please see a doctor.",
    }.get(category, "Unable to determine hypertension risk level.")


def _build_explanation(exp: dict) -> Optional[RiskExplanation]:
    if not exp:
        return None
    risk_factors = [
        RiskFactor(
            factor=rf["feature"],
            value=rf["value"],
            contribution=rf["shap_value"],
            direction=rf["direction"],
            explanation=(
                f"{rf['feature']} {rf['direction']} hypertension risk "
                f"by {abs(rf['shap_value']):.3f}"
            ),
        )
        for rf in exp.get("top_risk_factors", [])
    ]
    protective_factors = [
        RiskFactor(
            factor=pf["feature"],
            value=pf["value"],
            contribution=pf["shap_value"],
            direction=pf["direction"],
            explanation=(
                f"{pf['feature']} {pf['direction']} hypertension risk "
                f"by {abs(pf['shap_value']):.3f}"
            ),
        )
        for pf in exp.get("top_protective_factors", [])
    ]
    return RiskExplanation(
        base_risk=exp["base_risk"],
        risk_factors=risk_factors,
        protective_factors=protective_factors,
        summary=_explanation_summary(risk_factors, protective_factors),
    )


# ── Model info ─────────────────────────────────────────────────────────────────

@router.get("/model-info", response_model=HypertensionModelInfoResponse)
async def get_hypertension_model_info():
    """Get metadata about the loaded hypertension risk model."""
    if not hypertension_prediction_service.is_ready():
        raise HTTPException(
            status_code=503,
            detail=(
                "Hypertension model not loaded. "
                "Run: python src/ml/training/train_hypertension.py"
            ),
        )
    return HypertensionModelInfoResponse(
        **hypertension_prediction_service.get_model_info()
    )


# ── Full assessment ────────────────────────────────────────────────────────────

@router.post("/assess", response_model=HypertensionAssessmentResponse)
async def assess_hypertension_risk(request: HypertensionAssessmentRequest):
    """
    Comprehensive hypertension risk assessment.

    - Predicts hypertension risk from lifestyle and demographic factors
    - Blood pressure readings are NOT required (preventive model)
    - Optionally includes SHAP-based factor explanations
    - Optionally provides DASH/lifestyle recommendations
    """
    if not hypertension_prediction_service.is_ready():
        raise HTTPException(
            status_code=503,
            detail=(
                "Hypertension model not loaded. "
                "Run: python src/ml/training/train_hypertension.py"
            ),
        )

    try:
        metrics = request.metrics.model_dump()
        result = hypertension_prediction_service.predict(
            metrics, include_explanation=request.include_explanation
        )

        response_data = {
            "success": True,
            "assessment_id": result["assessment_id"],
            "timestamp": result["timestamp"],
            "risk": HypertensionRiskResult(
                risk_probability=result["risk"]["risk_probability"],
                risk_percentage=result["risk"]["risk_percentage"],
                risk_category=RiskCategory(result["risk"]["risk_category"]),
                prediction=result["risk"]["prediction"],
                confidence=result["risk"]["confidence"],
            ),
            "model_version": result["model_version"],
        }

        if request.include_explanation and result.get("explanation"):
            response_data["explanation"] = _build_explanation(result["explanation"])

        if request.include_recommendations:
            recs = hypertension_prediction_service.generate_recommendations(metrics, result)
            response_data["recommendations"] = [HealthRecommendation(**r) for r in recs]

        return HypertensionAssessmentResponse(**response_data)

    except Exception as e:
        logger.error(f"Hypertension assessment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Hypertension assessment failed: {str(e)}"
        )


# ── Quick check ────────────────────────────────────────────────────────────────

@router.post("/quick-check")
async def quick_hypertension_check(
    age: int = Query(..., ge=18, le=120, description="Age in years"),
    gender: str = Query(..., description="Gender (male/female)"),
    bmi: Optional[float] = Query(None, ge=10, le=80, description="BMI"),
    smoking: bool = Query(False, description="Current smoker"),
    diabetes: bool = Query(False, description="Known diabetes"),
):
    """
    Quick hypertension risk screening with minimal inputs.

    Blood pressure readings are intentionally excluded.
    """
    if not hypertension_prediction_service.is_ready():
        raise HTTPException(
            status_code=503,
            detail=(
                "Hypertension model not loaded. "
                "Run: python src/ml/training/train_hypertension.py"
            ),
        )

    metrics = {
        "age": age,
        "gender": gender,
        "bmi": bmi,
        "smoking_status": "current" if smoking else "never",
        "diabetes": diabetes,
    }

    result = hypertension_prediction_service.predict(metrics, include_explanation=False)
    return {
        "risk_percentage": result["risk"]["risk_percentage"],
        "risk_category":   result["risk"]["risk_category"],
        "message":         _risk_message(result["risk"]["risk_category"]),
    }


# ── Feature catalogue ──────────────────────────────────────────────────────────

@router.get("/features")
async def get_hypertension_features():
    """Return the feature catalogue for the hypertension assessment endpoint."""
    return {
        "features": [
            {"name": "age",               "description": "Age in years",                "type": "integer", "required": True,  "range": {"min": 18, "max": 120}},
            {"name": "gender",            "description": "Biological sex",              "type": "string",  "required": True,  "options": ["male", "female"]},
            {"name": "bmi",               "description": "Body Mass Index",             "type": "float",   "required": False, "range": {"min": 10, "max": 80}},
            {"name": "weight",            "description": "Weight (used to compute BMI if bmi omitted)", "type": "float", "required": False, "range": {"min": 20, "max": 500}, "unit": "kg"},
            {"name": "height",            "description": "Height (used to compute BMI if bmi omitted)", "type": "float", "required": False, "range": {"min": 50, "max": 300}, "unit": "cm"},
            {"name": "waist_circumference","description": "Waist circumference",        "type": "float",   "required": False, "range": {"min": 40, "max": 200}, "unit": "cm"},
            {"name": "total_cholesterol", "description": "Total cholesterol",           "type": "float",   "required": False, "range": {"min": 50, "max": 500},  "unit": "mg/dL"},
            {"name": "hdl_cholesterol",   "description": "HDL (good) cholesterol",      "type": "float",   "required": False, "range": {"min": 10, "max": 150},  "unit": "mg/dL"},
            {"name": "hba1c",             "description": "Glycated haemoglobin (HbA1c)","type": "float",   "required": False, "range": {"min": 3.0, "max": 20.0},"unit": "%"},
            {"name": "fasting_glucose",   "description": "Fasting glucose",             "type": "float",   "required": False, "range": {"min": 20, "max": 600},  "unit": "mg/dL"},
            {"name": "smoking_status",    "description": "Smoking status",              "type": "string",  "required": False, "options": ["never", "former", "current"]},
            {"name": "sedentary_minutes", "description": "Daily sedentary minutes",     "type": "integer", "required": False, "range": {"min": 0, "max": 1440}},
            {"name": "diabetes",          "description": "Known diabetes diagnosis",    "type": "boolean", "required": False},
            {"name": "education",         "description": "Education level (1=<9th grade … 5=college+)", "type": "integer", "required": False, "range": {"min": 1, "max": 5}},
            {"name": "income_ratio",      "description": "Family income to poverty ratio", "type": "float","required": False, "range": {"min": 0, "max": 10}},
        ],
        "note": (
            "Only age and gender are required. "
            "Blood pressure readings are intentionally excluded — "
            "this is a preventive risk model (predicts who is at risk of developing hypertension)."
        ),
    }
