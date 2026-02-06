"""
Test API Endpoints
==================
Integration tests for API routes.
"""

import pytest
from fastapi.testclient import TestClient


class TestRootEndpoints:
    """Tests for root endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data['name'] == "Preventive Health Assistant API"
        assert 'version' in data
        assert 'endpoints' in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == "healthy"
        assert 'model_loaded' in data


class TestHealthStatusEndpoint:
    """Tests for /api/v1/health/status endpoint."""

    def test_status_endpoint(self, client):
        """Test status endpoint returns service status."""
        response = client.get("/api/v1/health/status")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] in ['healthy', 'degraded']
        assert 'version' in data
        assert 'model_loaded' in data
        assert 'timestamp' in data


class TestModelInfoEndpoint:
    """Tests for /api/v1/health/model-info endpoint."""

    def test_model_info_endpoint(self, client):
        """Test model info endpoint."""
        response = client.get("/api/v1/health/model-info")

        assert response.status_code == 200
        data = response.json()
        assert data['model_name'] == "Diabetes Risk Prediction Model"
        assert 'version' in data
        assert 'n_features' in data
        assert 'feature_names' in data
        assert 'performance_metrics' in data


class TestDiabetesAssessmentEndpoint:
    """Tests for /api/v1/health/diabetes/assess endpoint."""

    def test_assess_with_full_metrics(self, client, sample_metrics):
        """Test assessment with complete health metrics."""
        response = client.post(
            "/api/v1/health/diabetes/assess",
            json={
                "metrics": sample_metrics,
                "include_explanation": True,
                "include_recommendations": True
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert data['success'] == True
        assert 'assessment_id' in data
        assert 'timestamp' in data
        assert 'risk' in data
        assert 'model_version' in data

        # Check risk fields
        risk = data['risk']
        assert 0 <= risk['risk_probability'] <= 1
        assert 0 <= risk['risk_percentage'] <= 100
        assert risk['risk_category'] in ['Low', 'Moderate', 'High', 'Very High']
        assert risk['prediction'] in [0, 1]
        assert 0 <= risk['confidence'] <= 1

    def test_assess_with_minimal_metrics(self, client, minimal_metrics):
        """Test assessment with only required fields."""
        response = client.post(
            "/api/v1/health/diabetes/assess",
            json={
                "metrics": minimal_metrics,
                "include_explanation": False,
                "include_recommendations": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert 'risk' in data

    def test_assess_includes_explanation(self, client, sample_metrics):
        """Test assessment includes explanation when requested."""
        response = client.post(
            "/api/v1/health/diabetes/assess",
            json={
                "metrics": sample_metrics,
                "include_explanation": True,
                "include_recommendations": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'explanation' in data
        assert data['explanation'] is not None

        explanation = data['explanation']
        assert 'base_risk' in explanation
        assert 'risk_factors' in explanation
        assert 'protective_factors' in explanation
        assert 'summary' in explanation

    def test_assess_includes_recommendations(self, client, sample_metrics):
        """Test assessment includes recommendations when requested."""
        response = client.post(
            "/api/v1/health/diabetes/assess",
            json={
                "metrics": sample_metrics,
                "include_explanation": False,
                "include_recommendations": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'recommendations' in data
        assert isinstance(data['recommendations'], list)

    def test_assess_excludes_explanation_when_not_requested(self, client, sample_metrics):
        """Test explanation is excluded when not requested."""
        response = client.post(
            "/api/v1/health/diabetes/assess",
            json={
                "metrics": sample_metrics,
                "include_explanation": False,
                "include_recommendations": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get('explanation') is None

    def test_assess_high_risk_individual(self, client, high_risk_metrics):
        """Test high-risk individual gets appropriate assessment."""
        response = client.post(
            "/api/v1/health/diabetes/assess",
            json={
                "metrics": high_risk_metrics,
                "include_explanation": True,
                "include_recommendations": True
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should be high risk
        assert data['risk']['risk_category'] in ['High', 'Very High']

        # Should have medical screening recommendation
        recs = data.get('recommendations', [])
        medical_recs = [r for r in recs if r['category'] == 'medical']
        assert len(medical_recs) > 0

    def test_assess_validation_error_missing_age(self, client):
        """Test validation error for missing required field."""
        response = client.post(
            "/api/v1/health/diabetes/assess",
            json={
                "metrics": {"gender": "male"},  # Missing age
                "include_explanation": False,
                "include_recommendations": False
            }
        )

        assert response.status_code == 422  # Validation error

    def test_assess_validation_error_invalid_age(self, client):
        """Test validation error for invalid age."""
        response = client.post(
            "/api/v1/health/diabetes/assess",
            json={
                "metrics": {"age": 10, "gender": "male"},  # Too young
                "include_explanation": False,
                "include_recommendations": False
            }
        )

        assert response.status_code == 422

    def test_assess_validation_error_invalid_gender(self, client):
        """Test validation error for invalid gender."""
        response = client.post(
            "/api/v1/health/diabetes/assess",
            json={
                "metrics": {"age": 30, "gender": "invalid"},
                "include_explanation": False,
                "include_recommendations": False
            }
        )

        assert response.status_code == 422


class TestQuickCheckEndpoint:
    """Tests for /api/v1/health/diabetes/quick-check endpoint."""

    def test_quick_check_minimal(self, client):
        """Test quick check with minimal parameters."""
        response = client.post(
            "/api/v1/health/diabetes/quick-check",
            params={"age": 45, "gender": "male"}
        )

        assert response.status_code == 200
        data = response.json()
        assert 'risk_percentage' in data
        assert 'risk_category' in data
        assert 'message' in data

    def test_quick_check_with_all_params(self, client):
        """Test quick check with all parameters."""
        response = client.post(
            "/api/v1/health/diabetes/quick-check",
            params={
                "age": 55,
                "gender": "male",
                "bmi": 32.0,
                "hba1c": 6.2,
                "family_history": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['risk_category'] in ['Low', 'Moderate', 'High', 'Very High']

    def test_quick_check_validation_error(self, client):
        """Test quick check validation error."""
        response = client.post(
            "/api/v1/health/diabetes/quick-check",
            params={"age": 10, "gender": "male"}  # Age too low
        )

        assert response.status_code == 422


class TestFeaturesEndpoint:
    """Tests for /api/v1/health/diabetes/features endpoint."""

    def test_features_endpoint(self, client):
        """Test features endpoint returns feature information."""
        response = client.get("/api/v1/health/diabetes/features")

        assert response.status_code == 200
        data = response.json()

        assert 'features' in data
        assert isinstance(data['features'], list)
        assert len(data['features']) > 0

        # Check first feature has expected structure
        feature = data['features'][0]
        assert 'name' in feature
        assert 'description' in feature
        assert 'type' in feature
        assert 'required' in feature


class TestBatchAssessmentEndpoint:
    """Tests for /api/v1/health/diabetes/batch-assess endpoint."""

    def test_batch_assess_multiple_patients(self, client, sample_metrics, low_risk_metrics):
        """Test batch assessment with multiple patients."""
        response = client.post(
            "/api/v1/health/diabetes/batch-assess",
            json=[sample_metrics, low_risk_metrics]
        )

        assert response.status_code == 200
        data = response.json()

        assert data['total'] == 2
        assert data['successful'] == 2
        assert len(data['results']) == 2

        for result in data['results']:
            assert result['success'] == True
            assert 'risk_percentage' in result
            assert 'risk_category' in result

    def test_batch_assess_empty_list(self, client):
        """Test batch assessment with empty list."""
        response = client.post(
            "/api/v1/health/diabetes/batch-assess",
            json=[]
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0

    def test_batch_assess_limit_exceeded(self, client, sample_metrics):
        """Test batch assessment rejects more than 100 patients."""
        # Create 101 patient records
        patients = [sample_metrics.copy() for _ in range(101)]

        response = client.post(
            "/api/v1/health/diabetes/batch-assess",
            json=patients
        )

        assert response.status_code == 400


class TestAPIDocumentation:
    """Tests for API documentation endpoints."""

    def test_openapi_json(self, client):
        """Test OpenAPI JSON schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert 'openapi' in data
        assert 'info' in data
        assert 'paths' in data

    def test_swagger_ui(self, client):
        """Test Swagger UI is available."""
        response = client.get("/docs")

        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_redoc(self, client):
        """Test ReDoc is available."""
        response = client.get("/redoc")

        assert response.status_code == 200