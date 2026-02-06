"""
Health Assessment Schemas
=========================
Pydantic models for API request/response validation.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


# ============== Enums for constrained values ==============

class RiskCategory(str, Enum):
    """Risk level categories."""
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    VERY_HIGH = "Very High"


class Gender(str, Enum):
    """Gender options."""
    MALE = "male"
    FEMALE = "female"


# ============== Request Schemas ==============

class HealthMetricsInput(BaseModel):
    """
    Input health metrics for risk assessment.

    All measurements should be in standard units:
    - Weight: kg
    - Height: cm
    - Blood glucose: mg/dL
    - HbA1c: percentage
    """

    # Demographics (required)
    age: int = Field(..., ge=18, le=120, description="Age in years")
    gender: Gender = Field(..., description="Gender (male/female)")

    # Anthropometric (optional)
    weight: Optional[float] = Field(None, ge=20, le=500, description="Weight in kg")
    height: Optional[float] = Field(None, ge=50, le=300, description="Height in cm")
    bmi: Optional[float] = Field(None, ge=10, le=80, description="Body Mass Index")
    waist_circumference: Optional[float] = Field(None, ge=40, le=200, description="Waist circumference in cm")

    # Lab results (optional)
    hba1c: Optional[float] = Field(None, ge=3.0, le=20.0, description="HbA1c percentage")
    fasting_glucose: Optional[float] = Field(None, ge=20, le=600, description="Fasting glucose (mg/dL)")
    total_cholesterol: Optional[float] = Field(None, ge=50, le=500, description="Total cholesterol (mg/dL)")
    hdl_cholesterol: Optional[float] = Field(None, ge=10, le=150, description="HDL cholesterol (mg/dL)")

    # Lifestyle factors (optional)
    smoking_status: Optional[str] = Field(None, description="Smoking status (never/former/current)")
    sedentary_minutes: Optional[int] = Field(None, ge=0, le=1440, description="Daily sedentary minutes")

    # Medical history (optional)
    family_diabetes: Optional[bool] = Field(None, description="Family history of diabetes")
    prediabetes: Optional[bool] = Field(None, description="Previously diagnosed with prediabetes")

    # Socioeconomic (optional)
    education: Optional[int] = Field(None, ge=1, le=5, description="Education level (1-5)")
    income_ratio: Optional[float] = Field(None, ge=0, le=10, description="Income to poverty ratio")

    @validator('bmi', always=True)
    def calculate_bmi(cls, v, values):
        """Calculate BMI if weight and height are provided but BMI is not."""
        if v is not None:
            return v
        weight = values.get('weight')
        height = values.get('height')
        if weight and height:
            height_m = height / 100
            return round(weight / (height_m ** 2), 1)
        return None

    class Config:
        # Example for API documentation
        json_schema_extra = {
            "example": {
                "age": 45,
                "gender": "male",
                "bmi": 28.5,
                "hba1c": 5.7,
                "fasting_glucose": 105,
                "family_diabetes": True
            }
        }


class DiabetesAssessmentRequest(BaseModel):
    """Request for diabetes risk assessment."""
    metrics: HealthMetricsInput
    include_explanation: bool = Field(True, description="Include SHAP-based explanation")
    include_recommendations: bool = Field(True, description="Include health recommendations")


# ============== Response Schemas ==============

class RiskFactor(BaseModel):
    """Individual risk factor contribution."""
    factor: str = Field(..., description="Name of the risk factor")
    value: Any = Field(..., description="Current value")
    contribution: float = Field(..., description="Contribution to risk score")
    direction: str = Field(..., description="Whether it increases or decreases risk")
    explanation: str = Field(..., description="Plain language explanation")


class HealthRecommendation(BaseModel):
    """Health recommendation based on risk factors."""
    category: str = Field(..., description="Category (diet, exercise, medical, etc.)")
    priority: str = Field(..., description="Priority level (high, medium, low)")
    recommendation: str = Field(..., description="The recommendation")
    rationale: str = Field(..., description="Why this is recommended")
    source: Optional[str] = Field(None, description="Evidence source (WHO, CDC, etc.)")


class DiabetesRiskResult(BaseModel):
    """Diabetes risk assessment result."""
    risk_probability: float = Field(..., ge=0, le=1, description="Probability of diabetes (0-1)")
    risk_percentage: float = Field(..., ge=0, le=100, description="Risk as percentage")
    risk_category: RiskCategory = Field(..., description="Risk level category")
    prediction: int = Field(..., description="Binary prediction (0=No, 1=Yes)")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence")


class RiskExplanation(BaseModel):
    """SHAP-based explanation of risk factors."""
    base_risk: float = Field(..., description="Population baseline risk")
    risk_factors: List[RiskFactor] = Field(..., description="Factors increasing risk")
    protective_factors: List[RiskFactor] = Field(..., description="Factors decreasing risk")
    summary: str = Field(..., description="Plain language summary")


class DiabetesAssessmentResponse(BaseModel):
    """Complete diabetes risk assessment response."""
    success: bool = Field(True, description="Whether assessment was successful")
    assessment_id: str = Field(..., description="Unique assessment identifier")
    timestamp: str = Field(..., description="Assessment timestamp")

    # Core results
    risk: DiabetesRiskResult = Field(..., description="Risk assessment results")

    # Optional detailed information
    explanation: Optional[RiskExplanation] = Field(None, description="Risk explanation")
    recommendations: Optional[List[HealthRecommendation]] = Field(None, description="Health recommendations")

    # Metadata
    model_version: str = Field(..., description="Model version used")
    disclaimer: str = Field(
        default="This assessment is for informational purposes only and should not replace professional medical advice.",
        description="Medical disclaimer"
    )


class HealthStatusResponse(BaseModel):
    """API health check response."""
    status: str
    version: str
    model_loaded: bool
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response schema."""
    success: bool = Field(False)
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ModelInfoResponse(BaseModel):
    """Model information response."""
    model_name: str
    version: str
    trained_at: str
    n_features: int
    feature_names: List[str]
    performance_metrics: Dict[str, float]