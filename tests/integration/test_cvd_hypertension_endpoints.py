"""
CVD & Hypertension Endpoint Tests
===================================
Integration tests for /api/v1/health/cvd/* and /api/v1/health/hypertension/*.
"""

import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.main import app
from src.api.services.cvd_prediction_service import cvd_prediction_service
from src.api.services.hypertension_prediction_service import hypertension_prediction_service


# Module-level flags set by the autouse fixture (evaluated at test-session startup)
_cvd_loaded: bool = False
_htn_loaded: bool = False


@pytest.fixture(scope="module", autouse=True)
def load_cvd_htn_models():
    """Load CVD and HTN models once for this module (skip if neither is trained)."""
    global _cvd_loaded, _htn_loaded
    _cvd_loaded = cvd_prediction_service.load_model()
    _htn_loaded = hypertension_prediction_service.load_model()
    if not _cvd_loaded and not _htn_loaded:
        pytest.skip("Neither CVD nor HTN model is available — run training scripts first.")
    yield


@pytest.fixture
def skip_if_no_cvd():
    """Skip the current test when the CVD model has not been trained."""
    if not _cvd_loaded:
        pytest.skip("CVD model not trained — run: python src/ml/training/train_cvd.py")


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── Shared metric fixtures ────────────────────────────────────────────────────

@pytest.fixture
def cvd_sample():
    return {
        "age": 55,
        "gender": "male",
        "systolic_bp": 138,
        "diastolic_bp": 88,
        "total_cholesterol": 225,
        "hdl_cholesterol": 40,
        "bmi": 29.0,
        "smoking_status": "former",
        "diabetes": False,
    }


@pytest.fixture
def cvd_high_risk():
    return {
        "age": 68,
        "gender": "male",
        "systolic_bp": 158,
        "diastolic_bp": 96,
        "total_cholesterol": 270,
        "hdl_cholesterol": 32,
        "bmi": 34.0,
        "smoking_status": "current",
        "diabetes": True,
    }


@pytest.fixture
def cvd_minimal():
    return {"age": 40, "gender": "female"}


@pytest.fixture
def htn_sample():
    return {
        "age": 50,
        "gender": "male",
        "bmi": 30.5,
        "total_cholesterol": 215,
        "hdl_cholesterol": 42,
        "smoking_status": "former",
        "diabetes": False,
        "sedentary_minutes": 600,
    }


@pytest.fixture
def htn_high_risk():
    return {
        "age": 60,
        "gender": "male",
        "bmi": 36.0,
        "waist_circumference": 112,
        "total_cholesterol": 255,
        "hdl_cholesterol": 34,
        "smoking_status": "current",
        "diabetes": True,
        "sedentary_minutes": 900,
    }


@pytest.fixture
def htn_minimal():
    return {"age": 35, "gender": "female"}


# ═══════════════════════════════════════════════════════════════
# CVD TESTS
# ═══════════════════════════════════════════════════════════════

class TestCVDFeatures:
    pytestmark = pytest.mark.usefixtures("skip_if_no_cvd")

    def test_features_endpoint(self, client):
        r = client.get("/api/v1/health/cvd/features")
        assert r.status_code == 200
        data = r.json()
        assert "features" in data
        names = [f["name"] for f in data["features"]]
        # Required fields must be documented
        assert "age" in names
        assert "gender" in names
        # Optional but supported fields must also appear
        assert "weight" in names
        assert "height" in names
        assert "education" in names
        assert "income_ratio" in names

    def test_model_info(self, client):
        r = client.get("/api/v1/health/cvd/model-info")
        # 200 if trained, 503 if not
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            data = r.json()
            assert "model_name" in data
            assert "n_features" in data


class TestCVDAssess:
    pytestmark = pytest.mark.usefixtures("skip_if_no_cvd")

    def test_assess_full_metrics(self, client, cvd_sample):
        r = client.post(
            "/api/v1/health/cvd/assess",
            json={"metrics": cvd_sample, "include_explanation": True, "include_recommendations": True},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        risk = data["risk"]
        assert 0 <= risk["risk_probability"] <= 1
        assert risk["risk_category"] in ("Low", "Moderate", "High", "Very High")
        assert risk["prediction"] in (0, 1)

    def test_assess_minimal_metrics(self, client, cvd_minimal):
        r = client.post(
            "/api/v1/health/cvd/assess",
            json={"metrics": cvd_minimal, "include_explanation": False, "include_recommendations": False},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_assess_includes_explanation(self, client, cvd_sample):
        r = client.post(
            "/api/v1/health/cvd/assess",
            json={"metrics": cvd_sample, "include_explanation": True, "include_recommendations": False},
        )
        assert r.status_code == 200
        exp = r.json().get("explanation")
        assert exp is not None
        assert "base_risk" in exp
        assert "risk_factors" in exp   # RiskExplanation schema key (not raw SHAP "top_risk_factors")

    def test_assess_includes_recommendations(self, client, cvd_sample):
        r = client.post(
            "/api/v1/health/cvd/assess",
            json={"metrics": cvd_sample, "include_explanation": False, "include_recommendations": True},
        )
        assert r.status_code == 200
        recs = r.json().get("recommendations")
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_assess_high_risk_gets_medical_recommendation(self, client, cvd_high_risk):
        r = client.post(
            "/api/v1/health/cvd/assess",
            json={"metrics": cvd_high_risk, "include_explanation": False, "include_recommendations": True},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["risk"]["risk_category"] in ("High", "Very High")
        medical = [rec for rec in data.get("recommendations", []) if rec["category"] == "medical"]
        assert len(medical) > 0

    def test_assess_validation_missing_age(self, client):
        r = client.post(
            "/api/v1/health/cvd/assess",
            json={"metrics": {"gender": "male"}, "include_explanation": False, "include_recommendations": False},
        )
        assert r.status_code == 422

    def test_assess_validation_invalid_age(self, client):
        r = client.post(
            "/api/v1/health/cvd/assess",
            json={"metrics": {"age": 5, "gender": "female"}, "include_explanation": False, "include_recommendations": False},
        )
        assert r.status_code == 422

    def test_assess_bmi_auto_calculated_from_weight_height(self, client):
        r = client.post(
            "/api/v1/health/cvd/assess",
            json={
                "metrics": {"age": 40, "gender": "male", "weight": 85, "height": 175},
                "include_explanation": False,
                "include_recommendations": False,
            },
        )
        assert r.status_code == 200

    def test_assess_bmi_impossible_values_ignored(self, client):
        """height=5cm would give BMI=320,000 — validator should return None and not crash."""
        r = client.post(
            "/api/v1/health/cvd/assess",
            json={
                "metrics": {"age": 40, "gender": "male", "weight": 80, "height": 5},
                "include_explanation": False,
                "include_recommendations": False,
            },
        )
        # Should still succeed (BMI silently dropped, not 422 or 500)
        assert r.status_code == 200


class TestCVDQuickCheck:
    pytestmark = pytest.mark.usefixtures("skip_if_no_cvd")

    def test_quick_check_minimal(self, client):
        r = client.post("/api/v1/health/cvd/quick-check", params={"age": 50, "gender": "male"})
        assert r.status_code == 200
        data = r.json()
        assert "risk_percentage" in data
        assert "risk_category" in data

    def test_quick_check_with_all_params(self, client):
        r = client.post(
            "/api/v1/health/cvd/quick-check",
            params={
                "age": 60,
                "gender": "male",
                "systolic_bp": 145,
                "total_cholesterol": 240,
                "smoking": True,
                "diabetes": True,
            },
        )
        assert r.status_code == 200

    def test_quick_check_invalid_age(self, client):
        r = client.post("/api/v1/health/cvd/quick-check", params={"age": 10, "gender": "male"})
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════
# HYPERTENSION TESTS
# ═══════════════════════════════════════════════════════════════

class TestHypertensionFeatures:
    def test_features_endpoint(self, client):
        r = client.get("/api/v1/health/hypertension/features")
        assert r.status_code == 200
        data = r.json()
        names = [f["name"] for f in data["features"]]
        assert "age" in names
        assert "gender" in names
        assert "weight" in names
        assert "height" in names
        assert "education" in names
        # Blood pressure must NOT appear (preventive model)
        assert "systolic_bp" not in names
        assert "diastolic_bp" not in names

    def test_features_note_mentions_preventive(self, client):
        r = client.get("/api/v1/health/hypertension/features")
        note = r.json().get("note", "").lower()
        assert "preventive" in note or "blood pressure" in note.lower()


class TestHypertensionAssess:
    def test_assess_full_metrics(self, client, htn_sample):
        r = client.post(
            "/api/v1/health/hypertension/assess",
            json={"metrics": htn_sample, "include_explanation": True, "include_recommendations": True},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        risk = data["risk"]
        assert 0 <= risk["risk_probability"] <= 1
        assert risk["risk_category"] in ("Low", "Moderate", "High", "Very High")

    def test_assess_minimal_metrics(self, client, htn_minimal):
        r = client.post(
            "/api/v1/health/hypertension/assess",
            json={"metrics": htn_minimal, "include_explanation": False, "include_recommendations": False},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_assess_high_risk(self, client, htn_high_risk):
        r = client.post(
            "/api/v1/health/hypertension/assess",
            json={"metrics": htn_high_risk, "include_explanation": False, "include_recommendations": True},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["risk"]["risk_category"] in ("Moderate", "High", "Very High")

    def test_assess_excludes_bp_inputs(self, client):
        """Passing systolic_bp should be silently ignored (field not in schema)."""
        r = client.post(
            "/api/v1/health/hypertension/assess",
            json={
                "metrics": {"age": 50, "gender": "male", "systolic_bp": 145},
                "include_explanation": False,
                "include_recommendations": False,
            },
        )
        # 422 because systolic_bp is not in HypertensionMetricsInput
        assert r.status_code == 422

    def test_assess_validation_missing_gender(self, client):
        r = client.post(
            "/api/v1/health/hypertension/assess",
            json={"metrics": {"age": 45}, "include_explanation": False, "include_recommendations": False},
        )
        assert r.status_code == 422

    def test_assess_bmi_impossible_values_ignored(self, client):
        r = client.post(
            "/api/v1/health/hypertension/assess",
            json={
                "metrics": {"age": 45, "gender": "female", "weight": 70, "height": 3},
                "include_explanation": False,
                "include_recommendations": False,
            },
        )
        assert r.status_code == 200


class TestHypertensionQuickCheck:
    def test_quick_check_minimal(self, client):
        r = client.post("/api/v1/health/hypertension/quick-check", params={"age": 45, "gender": "male"})
        assert r.status_code == 200
        data = r.json()
        assert "risk_percentage" in data
        assert "risk_category" in data

    def test_quick_check_with_optional_params(self, client):
        r = client.post(
            "/api/v1/health/hypertension/quick-check",
            params={"age": 55, "gender": "male", "bmi": 32.0, "smoking": True, "diabetes": True},
        )
        assert r.status_code == 200

    def test_quick_check_invalid_age(self, client):
        r = client.post("/api/v1/health/hypertension/quick-check", params={"age": 10, "gender": "female"})
        assert r.status_code == 422
