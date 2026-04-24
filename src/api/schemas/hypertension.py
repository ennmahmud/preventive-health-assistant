"""
Hypertension Assessment Schemas
================================
Pydantic models for hypertension risk assessment API request/response validation.

Note: Blood pressure readings are intentionally EXCLUDED from the input schema.
The hypertension model is a preventive model — it predicts BP risk from
lifestyle/demographic factors so users without a BP reading can still be assessed.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator
from src.api.schemas.health import (
    Gender,
    RiskCategory,
    RiskFactor,
    RiskExplanation,
    HealthRecommendation,
)


# ── Request Schemas ────────────────────────────────────────────────────────────

class HypertensionMetricsInput(BaseModel):
    """
    Input health metrics for hypertension risk assessment.

    Blood pressure readings are deliberately excluded — using them as features
    would be circular since the model's target IS defined from BP measurements.
    This makes the model useful for preventive screening.
    """

    # Demographics (required)
    age: int = Field(..., ge=18, le=120, description="Age in years")
    gender: Gender = Field(..., description="Gender (male/female)")

    # Anthropometric (optional)
    weight: Optional[float] = Field(None, ge=20, le=500, description="Weight in kg")
    height: Optional[float] = Field(None, ge=1, le=300, description="Height in cm")
    bmi: Optional[float] = Field(None, ge=10, le=80, description="Body Mass Index")
    waist_circumference: Optional[float] = Field(
        None, ge=40, le=200, description="Waist circumference in cm"
    )

    # Blood pressure (optional — significantly improves accuracy when known)
    systolic_bp: Optional[float] = Field(
        None, ge=60, le=260, description="Systolic blood pressure (mmHg)"
    )
    diastolic_bp: Optional[float] = Field(
        None, ge=30, le=160, description="Diastolic blood pressure (mmHg)"
    )

    # Lab results (optional)
    hba1c: Optional[float] = Field(None, ge=3.0, le=20.0, description="HbA1c percentage")
    fasting_glucose: Optional[float] = Field(
        None, ge=20, le=600, description="Fasting glucose (mg/dL)"
    )
    total_cholesterol: Optional[float] = Field(
        None, ge=50, le=500, description="Total cholesterol (mg/dL)"
    )
    hdl_cholesterol: Optional[float] = Field(
        None, ge=10, le=150, description="HDL cholesterol (mg/dL)"
    )

    # Lifestyle (optional)
    smoking_status: Optional[str] = Field(
        None, description="Smoking status (never/former/current)"
    )
    sedentary_minutes: Optional[int] = Field(
        None, ge=0, le=1440, description="Daily sedentary minutes"
    )

    # Medical history (optional)
    diabetes: Optional[bool] = Field(None, description="Known diabetes diagnosis")

    # Socioeconomic (optional)
    education: Optional[int] = Field(None, ge=1, le=5, description="Education level (1-5)")
    income_ratio: Optional[float] = Field(
        None, ge=0, le=10, description="Income to poverty ratio"
    )

    @validator("bmi", always=True)
    def calculate_bmi(cls, v, values):
        if v is not None:
            return v
        weight = values.get("weight")
        height = values.get("height")
        if weight and height and height > 0:
            calculated = round(weight / ((height / 100) ** 2), 1)
            # Reject physiologically impossible values (height or weight badly wrong)
            if 10.0 <= calculated <= 80.0:
                return calculated
        return None

    class Config:
        json_schema_extra = {
            "example": {
                "age": 48,
                "gender": "male",
                "bmi": 31.2,
                "systolic_bp": 138,
                "diastolic_bp": 88,
                "smoking_status": "never",
                "sedentary_minutes": 600,
                "diabetes": False,
            }
        }


class HypertensionAssessmentRequest(BaseModel):
    """Request body for hypertension risk assessment."""

    metrics: HypertensionMetricsInput
    include_explanation: bool = Field(True, description="Include SHAP-based explanation")
    include_recommendations: bool = Field(True, description="Include health recommendations")


# ── Response Schemas ───────────────────────────────────────────────────────────

class HypertensionRiskResult(BaseModel):
    """Hypertension risk assessment result."""

    risk_probability: float = Field(..., ge=0, le=1, description="Probability of hypertension (0-1)")
    risk_percentage: float = Field(..., ge=0, le=100, description="Risk as percentage")
    risk_category: RiskCategory = Field(..., description="Risk level category")
    prediction: int = Field(..., description="Binary prediction (0=Low risk, 1=High risk)")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence")


class HypertensionAssessmentResponse(BaseModel):
    """Complete hypertension risk assessment response."""

    success: bool = Field(True)
    assessment_id: str
    timestamp: str

    risk: HypertensionRiskResult
    explanation: Optional[RiskExplanation] = None
    recommendations: Optional[List[HealthRecommendation]] = None

    model_version: str
    disclaimer: str = Field(
        default=(
            "This hypertension risk assessment is for informational purposes only "
            "and does not replace professional medical advice or blood pressure measurement."
        )
    )


class HypertensionModelInfoResponse(BaseModel):
    """Hypertension model metadata response."""

    model_name: str
    version: str
    trained_at: str
    n_features: int
    feature_names: List[str]
    performance_metrics: Dict[str, float]
