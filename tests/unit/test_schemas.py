"""
Test API Schemas
================
Unit tests for Pydantic model validation.
"""

import pytest
from pydantic import ValidationError

from src.api.schemas.health import (
    HealthMetricsInput,
    DiabetesAssessmentRequest,
    DiabetesRiskResult,
    RiskCategory,
    Gender
)


class TestHealthMetricsInput:
    """Tests for HealthMetricsInput schema."""

    def test_valid_minimal_input(self):
        """Test with only required fields."""
        metrics = HealthMetricsInput(age=45, gender="male")

        assert metrics.age == 45
        assert metrics.gender == Gender.MALE
        assert metrics.bmi is None  # Optional field

    def test_valid_full_input(self, sample_metrics):
        """Test with all fields provided."""
        metrics = HealthMetricsInput(**sample_metrics)

        assert metrics.age == 45
        assert metrics.gender == Gender.MALE
        assert metrics.bmi == 28.5
        assert metrics.hba1c == 5.7
        assert metrics.family_diabetes == True

    def test_bmi_auto_calculation(self):
        """Test BMI is calculated from weight and height."""
        metrics = HealthMetricsInput(
            age=30,
            gender="female",
            weight=70,  # kg
            height=165  # cm
        )

        # BMI = 70 / (1.65)^2 = 25.7
        assert metrics.bmi is not None
        assert 25.5 <= metrics.bmi <= 26.0

    def test_bmi_not_overwritten_if_provided(self):
        """Test provided BMI is not overwritten by calculation."""
        metrics = HealthMetricsInput(
            age=30,
            gender="female",
            weight=70,
            height=165,
            bmi=30.0  # Explicitly provided
        )

        assert metrics.bmi == 30.0  # Should keep provided value

    def test_age_validation_too_young(self):
        """Test age validation rejects minors."""
        with pytest.raises(ValidationError) as exc_info:
            HealthMetricsInput(age=15, gender="male")

        assert "age" in str(exc_info.value)

    def test_age_validation_too_old(self):
        """Test age validation rejects unrealistic ages."""
        with pytest.raises(ValidationError) as exc_info:
            HealthMetricsInput(age=150, gender="male")

        assert "age" in str(exc_info.value)

    def test_invalid_gender(self):
        """Test gender validation rejects invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            HealthMetricsInput(age=30, gender="other")

        assert "gender" in str(exc_info.value)

    def test_bmi_validation_range(self):
        """Test BMI validation rejects out-of-range values."""
        with pytest.raises(ValidationError):
            HealthMetricsInput(age=30, gender="male", bmi=5.0)  # Too low

        with pytest.raises(ValidationError):
            HealthMetricsInput(age=30, gender="male", bmi=100.0)  # Too high

    def test_hba1c_validation_range(self):
        """Test HbA1c validation range."""
        # Valid values
        metrics = HealthMetricsInput(age=30, gender="male", hba1c=5.7)
        assert metrics.hba1c == 5.7

        # Invalid - too low
        with pytest.raises(ValidationError):
            HealthMetricsInput(age=30, gender="male", hba1c=2.0)

        # Invalid - too high
        with pytest.raises(ValidationError):
            HealthMetricsInput(age=30, gender="male", hba1c=25.0)

    def test_optional_fields_default_to_none(self):
        """Test optional fields are None when not provided."""
        metrics = HealthMetricsInput(age=30, gender="male")

        assert metrics.weight is None
        assert metrics.height is None
        assert metrics.hba1c is None
        assert metrics.fasting_glucose is None
        assert metrics.smoking_status is None
        assert metrics.family_diabetes is None


class TestDiabetesAssessmentRequest:
    """Tests for DiabetesAssessmentRequest schema."""

    def test_valid_request(self, sample_metrics):
        """Test valid assessment request."""
        request = DiabetesAssessmentRequest(
            metrics=HealthMetricsInput(**sample_metrics),
            include_explanation=True,
            include_recommendations=True
        )

        assert request.metrics.age == 45
        assert request.include_explanation == True
        assert request.include_recommendations == True

    def test_default_flags(self, minimal_metrics):
        """Test default values for explanation and recommendations flags."""
        request = DiabetesAssessmentRequest(
            metrics=HealthMetricsInput(**minimal_metrics)
        )

        # Defaults should be True
        assert request.include_explanation == True
        assert request.include_recommendations == True

    def test_flags_can_be_disabled(self, minimal_metrics):
        """Test flags can be set to False."""
        request = DiabetesAssessmentRequest(
            metrics=HealthMetricsInput(**minimal_metrics),
            include_explanation=False,
            include_recommendations=False
        )

        assert request.include_explanation == False
        assert request.include_recommendations == False


class TestDiabetesRiskResult:
    """Tests for DiabetesRiskResult schema."""

    def test_valid_result(self):
        """Test valid risk result."""
        result = DiabetesRiskResult(
            risk_probability=0.35,
            risk_percentage=35.0,
            risk_category=RiskCategory.MODERATE,
            prediction=0,
            confidence=0.85
        )

        assert result.risk_probability == 0.35
        assert result.risk_category == RiskCategory.MODERATE

    def test_probability_validation(self):
        """Test probability must be between 0 and 1."""
        with pytest.raises(ValidationError):
            DiabetesRiskResult(
                risk_probability=1.5,  # Invalid
                risk_percentage=150.0,
                risk_category=RiskCategory.HIGH,
                prediction=1,
                confidence=0.9
            )

    def test_risk_categories(self):
        """Test all risk categories are valid."""
        for category in RiskCategory:
            result = DiabetesRiskResult(
                risk_probability=0.5,
                risk_percentage=50.0,
                risk_category=category,
                prediction=0,
                confidence=0.8
            )
            assert result.risk_category == category