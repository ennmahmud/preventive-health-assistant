"""
Health Assessment Routes
========================
API endpoints for health risk assessments.
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from src.api.auth import require_api_key

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.api.schemas.health import (
    HealthMetricsInput,
    DiabetesAssessmentRequest,
    DiabetesAssessmentResponse,
    DiabetesRiskResult,
    RiskExplanation,
    RiskFactor,
    HealthRecommendation,
    HealthStatusResponse,
    ModelInfoResponse,
    RiskCategory
)
from src.api.services.prediction_service import prediction_service
from typing import List

logger = logging.getLogger(__name__)

# Create router with prefix and tags (for documentation grouping)
router = APIRouter(
    prefix="/api/v1/health",
    tags=["Health Assessments"],
    dependencies=[Depends(require_api_key)],
)


# ============== Health Check Endpoints ==============

@router.get("/status", response_model=HealthStatusResponse)
async def health_status():
    """Check the health status of the API."""
    return HealthStatusResponse(
        status="healthy" if prediction_service.is_ready() else "degraded",
        version="1.0.0",
        model_loaded=prediction_service.is_ready(),
        timestamp=datetime.now().isoformat()
    )


@router.get("/model-info", response_model=ModelInfoResponse)
async def get_model_info():
    """Get information about the loaded ML model."""
    if not prediction_service.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service is starting up."
        )

    info = prediction_service.get_model_info()
    return ModelInfoResponse(**info)


# ============== Main Assessment Endpoint ==============

@router.post("/diabetes/assess", response_model=DiabetesAssessmentResponse)
async def assess_diabetes_risk(request: DiabetesAssessmentRequest):
    """
    Perform a comprehensive diabetes risk assessment.

    This endpoint:
    - Analyzes health metrics to predict diabetes risk
    - Provides probability score and risk category
    - Optionally includes SHAP-based explanations
    - Optionally provides personalized recommendations
    """
    if not prediction_service.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please try again in a moment."
        )

    try:
        # Convert Pydantic model to dictionary
        metrics = request.metrics.model_dump()

        # Get prediction from service
        result = prediction_service.predict(
            metrics,
            include_explanation=request.include_explanation
        )

        # Build response
        response_data = {
            'success': True,
            'assessment_id': result['assessment_id'],
            'timestamp': result['timestamp'],
            'risk': DiabetesRiskResult(
                risk_probability=result['risk']['risk_probability'],
                risk_percentage=result['risk']['risk_percentage'],
                risk_category=RiskCategory(result['risk']['risk_category']),
                prediction=result['risk']['prediction'],
                confidence=result['risk']['confidence']
            ),
            'model_version': result['model_version']
        }

        # Add explanation if requested
        if request.include_explanation and result.get('explanation'):
            exp = result['explanation']
            # Transform SHAP output to match our schema
            risk_factors = []
            for rf in exp.get('top_risk_factors', []):
                risk_factors.append(RiskFactor(
                    factor=rf['feature'],
                    value=rf['value'],
                    contribution=rf['shap_value'],
                    direction=rf['direction'],
                    explanation=f"{rf['feature']} {rf['direction']} risk by {abs(rf['shap_value']):.3f}"
                ))

            protective_factors = []
            for pf in exp.get('top_protective_factors', []):
                protective_factors.append(RiskFactor(
                    factor=pf['feature'],
                    value=pf['value'],
                    contribution=pf['shap_value'],
                    direction=pf['direction'],
                    explanation=f"{pf['feature']} {pf['direction']} risk by {abs(pf['shap_value']):.3f}"
                ))

            # Generate summary
            summary = _generate_explanation_summary(risk_factors, protective_factors)

            response_data['explanation'] = RiskExplanation(
                base_risk=exp['base_risk'],
                risk_factors=risk_factors,
                protective_factors=protective_factors,
                summary=summary
            )

        # Add recommendations if requested
        if request.include_recommendations:
            recs = prediction_service.generate_recommendations(metrics, result)
            response_data['recommendations'] = [
                HealthRecommendation(**rec) for rec in recs
            ]

        return DiabetesAssessmentResponse(**response_data)

    except Exception as e:
        logger.error(f"Assessment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Assessment failed: {str(e)}"
        )


# ============== Quick Check Endpoint ==============

@router.post("/diabetes/quick-check")
async def quick_diabetes_check(
        age: int = Query(..., ge=18, le=120, description="Age in years"),
        gender: str = Query(..., description="Gender (male/female)"),
        bmi: Optional[float] = Query(None, ge=10, le=80, description="BMI"),
        hba1c: Optional[float] = Query(None, ge=3, le=20, description="HbA1c %"),
        family_history: bool = Query(False, description="Family history of diabetes")
):
    """
    Quick diabetes risk check with minimal inputs.

    A simplified endpoint for basic risk screening.
    """
    if not prediction_service.is_ready():
        raise HTTPException(status_code=503, detail="Model not loaded")

    metrics = {
        'age': age,
        'gender': gender,
        'bmi': bmi,
        'hba1c': hba1c,
        'family_diabetes': family_history
    }

    result = prediction_service.predict(metrics, include_explanation=False)

    return {
        'risk_percentage': result['risk']['risk_percentage'],
        'risk_category': result['risk']['risk_category'],
        'message': _get_risk_message(result['risk']['risk_category'])
    }


def _get_risk_message(category: str) -> str:
    """Get a brief message for the risk category."""
    messages = {
        'Low': "Your diabetes risk appears to be low. Continue maintaining a healthy lifestyle.",
        'Moderate': "You have some risk factors. Consider lifestyle modifications and regular check-ups.",
        'High': "Your risk is elevated. We recommend consulting with a healthcare provider.",
        'Very High': "Your risk is significantly elevated. Please consult a healthcare provider soon."
    }
    return messages.get(category, "Unable to determine risk level.")


def _generate_explanation_summary(risk_factors: List[RiskFactor], protective_factors: List[RiskFactor]) -> str:
    """Generate a human-readable summary from risk factors."""
    parts = []

    if risk_factors:
        risk_names = [rf.factor for rf in risk_factors[:3]]
        parts.append(f"Key factors increasing your risk: {', '.join(risk_names)}")

    if protective_factors:
        protective_names = [pf.factor for pf in protective_factors[:3]]
        parts.append(f"Factors working in your favor: {', '.join(protective_names)}")

    if not parts:
        return "Your risk assessment is based on a combination of health metrics."

    return ". ".join(parts) + "."


# ============== Feature Information Endpoint ==============

@router.get("/diabetes/features")
async def get_required_features():
    """Get information about the features used for assessment."""
    features = [
        {
            "name": "age",
            "description": "Age in years",
            "type": "integer",
            "required": True,
            "range": {"min": 18, "max": 120}
        },
        {
            "name": "gender",
            "description": "Biological sex",
            "type": "string",
            "required": True,
            "options": ["male", "female"]
        },
        {
            "name": "bmi",
            "description": "Body Mass Index",
            "type": "float",
            "required": False,
            "range": {"min": 10, "max": 80}
        },
        {
            "name": "hba1c",
            "description": "Glycated hemoglobin",
            "type": "float",
            "required": False,
            "range": {"min": 3.0, "max": 20.0},
            "reference": {"normal": "<5.7", "prediabetes": "5.7-6.4", "diabetes": "≥6.5"}
        },
        # ... more features
    ]

    return {"features": features, "note": "More features = more accurate assessment"}



@router.post(
    "/diabetes/batch-assess",
    summary="Batch diabetes risk assessment",
    description="Assess diabetes risk for multiple patients at once"
)
async def batch_assess_diabetes_risk(
        patients: List[HealthMetricsInput]
):
    """
    Batch assess diabetes risk for multiple patients.

    Limit: 100 patients per request
    """
    # Validate batch size
    if len(patients) > 100:
        raise HTTPException(
            status_code=400,
            detail="Batch size exceeds maximum of 100 patients"
        )

    if len(patients) == 0:
        return {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "results": []
        }

    if not prediction_service.is_ready():
        raise HTTPException(status_code=503, detail="Model not loaded")

    results = []
    successful = 0
    failed = 0

    for patient in patients:
        try:
            metrics = patient.model_dump()
            result = prediction_service.predict(metrics, include_explanation=False)
            results.append({
                "success": True,
                "risk_percentage": result["risk"]["risk_percentage"],
                "risk_category": result["risk"]["risk_category"],
                "risk_probability": result["risk"]["risk_probability"],
            })
            successful += 1
        except Exception as e:
            logger.error(f"Failed to assess patient: {str(e)}")
            results.append({
                "success": False,
                "error": str(e)
            })
            failed += 1

    return {
        "total": len(patients),
        "successful": successful,
        "failed": failed,
        "results": results
    }