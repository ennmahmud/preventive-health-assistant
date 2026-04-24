"""
CVD Assessment Routes
=====================
API endpoints for cardiovascular disease (CVD) risk assessments.

Endpoints:
  POST /api/v1/health/cvd/assess         — full assessment with explanation & recommendations
  POST /api/v1/health/cvd/quick-check    — minimal-input screening
  GET  /api/v1/health/cvd/model-info     — loaded model metadata
  GET  /api/v1/health/cvd/features       — feature catalogue
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.auth import require_api_key

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.api.schemas.health import RiskCategory, RiskFactor, RiskExplanation, HealthRecommendation
from src.api.schemas.cvd import (
    CVDMetricsInput,
    CVDAssessmentRequest,
    CVDAssessmentResponse,
    CVDRiskResult,
    CVDModelInfoResponse,
)
from src.api.services.cvd_prediction_service import cvd_prediction_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/health/cvd",
    tags=["CVD Assessments"],
    dependencies=[Depends(require_api_key)],
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _explanation_summary(
    risk_factors: List[RiskFactor], protective_factors: List[RiskFactor]
) -> str:
    parts = []
    if risk_factors:
        names = [rf.factor for rf in risk_factors[:3]]
        parts.append(f"Key factors increasing your CVD risk: {', '.join(names)}")
    if protective_factors:
        names = [pf.factor for pf in protective_factors[:3]]
        parts.append(f"Factors working in your favour: {', '.join(names)}")
    return (". ".join(parts) + ".") if parts else (
        "Your CVD risk assessment is based on a combination of health metrics."
    )


def _risk_message(category: str) -> str:
    return {
        "Low":       "Your CVD risk appears low. Keep up healthy habits.",
        "Moderate":  "You have some CVD risk factors. Lifestyle modifications are recommended.",
        "High":      "Your CVD risk is elevated. Please consult a healthcare provider.",
        "Very High": "Your CVD risk is significantly elevated. Please seek medical advice soon.",
    }.get(category, "Unable to determine CVD risk level.")


def _build_explanation(exp: dict) -> Optional[RiskExplanation]:
    """Transform SHAP output dict → RiskExplanation schema."""
    if not exp:
        return None

    risk_factors = [
        RiskFactor(
            factor=rf["feature"],
            value=rf["value"],
            contribution=rf["shap_value"],
            direction=rf["direction"],
            explanation=f"{rf['feature']} {rf['direction']} CVD risk by {abs(rf['shap_value']):.3f}",
        )
        for rf in exp.get("top_risk_factors", [])
    ]
    protective_factors = [
        RiskFactor(
            factor=pf["feature"],
            value=pf["value"],
            contribution=pf["shap_value"],
            direction=pf["direction"],
            explanation=f"{pf['feature']} {pf['direction']} CVD risk by {abs(pf['shap_value']):.3f}",
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

@router.get("/model-info", response_model=CVDModelInfoResponse)
async def get_cvd_model_info():
    """Get metadata about the loaded CVD risk model."""
    if not cvd_prediction_service.is_ready():
        raise HTTPException(
            status_code=503,
            detail="CVD model not loaded. Run: python src/ml/training/train_cvd.py",
        )
    return CVDModelInfoResponse(**cvd_prediction_service.get_model_info())


# ── Full assessment ────────────────────────────────────────────────────────────

@router.post("/assess", response_model=CVDAssessmentResponse)
async def assess_cvd_risk(request: CVDAssessmentRequest):
    """
    Comprehensive CVD risk assessment.

    - Predicts 10-year CVD risk probability using Framingham-style features
    - Optionally includes SHAP-based factor explanations
    - Optionally provides evidence-based recommendations
    """
    if not cvd_prediction_service.is_ready():
        raise HTTPException(
            status_code=503,
            detail="CVD model not loaded. Run: python src/ml/training/train_cvd.py",
        )

    try:
        metrics = request.metrics.model_dump()
        result = cvd_prediction_service.predict(
            metrics, include_explanation=request.include_explanation
        )

        response_data = {
            "success": True,
            "assessment_id": result["assessment_id"],
            "timestamp": result["timestamp"],
            "risk": CVDRiskResult(
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
            recs = cvd_prediction_service.generate_recommendations(metrics, result)
            response_data["recommendations"] = [HealthRecommendation(**r) for r in recs]

        return CVDAssessmentResponse(**response_data)

    except Exception as e:
        logger.error(f"CVD assessment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"CVD assessment failed: {str(e)}")


# ── Quick check ────────────────────────────────────────────────────────────────

@router.post("/quick-check")
async def quick_cvd_check(
    age: int = Query(..., ge=18, le=120, description="Age in years"),
    gender: str = Query(..., description="Gender (male/female)"),
    systolic_bp: Optional[float] = Query(None, ge=60, le=250, description="Systolic BP (mmHg)"),
    total_cholesterol: Optional[float] = Query(None, ge=50, le=500, description="Total cholesterol (mg/dL)"),
    smoking: bool = Query(False, description="Current smoker"),
    diabetes: bool = Query(False, description="Known diabetes"),
):
    """
    Quick CVD risk screening with minimal inputs.

    Accepts the most impactful Framingham risk variables only.
    """
    if not cvd_prediction_service.is_ready():
        raise HTTPException(
            status_code=503,
            detail="CVD model not loaded. Run: python src/ml/training/train_cvd.py",
        )

    metrics = {
        "age": age,
        "gender": gender,
        "systolic_bp": systolic_bp,
        "total_cholesterol": total_cholesterol,
        "smoking_status": "current" if smoking else "never",
        "diabetes": diabetes,
    }

    result = cvd_prediction_service.predict(metrics, include_explanation=False)
    return {
        "risk_percentage": result["risk"]["risk_percentage"],
        "risk_category":   result["risk"]["risk_category"],
        "message":         _risk_message(result["risk"]["risk_category"]),
    }


# ── Feature catalogue ──────────────────────────────────────────────────────────

@router.get("/features")
async def get_cvd_features():
    """Return the feature catalogue for the CVD assessment endpoint."""
    return {
        "features": [
            {"name": "age",               "description": "Age in years",                "type": "integer", "required": True,  "range": {"min": 18, "max": 120}},
            {"name": "gender",            "description": "Biological sex",              "type": "string",  "required": True,  "options": ["male", "female"]},
            {"name": "systolic_bp",       "description": "Systolic blood pressure",     "type": "float",   "required": False, "range": {"min": 60, "max": 250}, "unit": "mmHg"},
            {"name": "diastolic_bp",      "description": "Diastolic blood pressure",    "type": "float",   "required": False, "range": {"min": 30, "max": 150}, "unit": "mmHg"},
            {"name": "total_cholesterol", "description": "Total cholesterol",           "type": "float",   "required": False, "range": {"min": 50, "max": 500},  "unit": "mg/dL"},
            {"name": "hdl_cholesterol",   "description": "HDL (good) cholesterol",      "type": "float",   "required": False, "range": {"min": 10, "max": 150},  "unit": "mg/dL"},
            {"name": "bmi",               "description": "Body Mass Index",             "type": "float",   "required": False, "range": {"min": 10, "max": 80}},
            {"name": "weight",            "description": "Weight (used to compute BMI if bmi omitted)", "type": "float", "required": False, "range": {"min": 20, "max": 500}, "unit": "kg"},
            {"name": "height",            "description": "Height (used to compute BMI if bmi omitted)", "type": "float", "required": False, "range": {"min": 50, "max": 300}, "unit": "cm"},
            {"name": "waist_circumference","description": "Waist circumference",        "type": "float",   "required": False, "range": {"min": 40, "max": 200}, "unit": "cm"},
            {"name": "hba1c",             "description": "Glycated haemoglobin (HbA1c)","type": "float",   "required": False, "range": {"min": 3.0, "max": 20.0},"unit": "%"},
            {"name": "fasting_glucose",   "description": "Fasting glucose",             "type": "float",   "required": False, "range": {"min": 20, "max": 600},  "unit": "mg/dL"},
            {"name": "smoking_status",    "description": "Smoking status",              "type": "string",  "required": False, "options": ["never", "former", "current"]},
            {"name": "sedentary_minutes", "description": "Daily sedentary minutes",     "type": "integer", "required": False, "range": {"min": 0, "max": 1440}},
            {"name": "diabetes",          "description": "Known diabetes diagnosis",    "type": "boolean", "required": False},
            {"name": "education",         "description": "Education level (1=<9th grade … 5=college+)", "type": "integer", "required": False, "range": {"min": 1, "max": 5}},
            {"name": "income_ratio",      "description": "Family income to poverty ratio", "type": "float","required": False, "range": {"min": 0, "max": 10}},
        ],
        "note": "Only age and gender are required. More fields provided → more accurate CVD risk estimate.",
    }
