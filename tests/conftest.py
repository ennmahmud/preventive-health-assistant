"""
Pytest Configuration and Fixtures
=================================
Shared test setup used across all test files.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.main import app
from src.api.services.prediction_service import prediction_service


@pytest.fixture(scope="session", autouse=True)
def load_model():
    """
    Load the ML model once for all tests.

    scope="session" means this runs once per test session, not per test.
    autouse=True means it runs automatically without explicit request.
    """
    success = prediction_service.load_model()
    if not success:
        pytest.skip("Model not available - skipping tests that require it")
    yield
    # Cleanup would go here if needed


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI app.

    TestClient allows us to make HTTP requests without running the server.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_metrics():
    """Sample health metrics for testing."""
    return {
        "age": 45,
        "gender": "male",
        "bmi": 28.5,
        "hba1c": 5.7,
        "fasting_glucose": 105,
        "total_cholesterol": 210,
        "hdl_cholesterol": 45,
        "waist_circumference": 102,
        "smoking_status": "former",
        "family_diabetes": True
    }


@pytest.fixture
def high_risk_metrics():
    """Health metrics for a high-risk individual."""
    return {
        "age": 65,
        "gender": "male",
        "bmi": 35.0,
        "hba1c": 6.8,
        "fasting_glucose": 140,
        "total_cholesterol": 280,
        "hdl_cholesterol": 35,
        "waist_circumference": 115,
        "smoking_status": "current",
        "family_diabetes": True,
        "prediabetes": True
    }


@pytest.fixture
def low_risk_metrics():
    """Health metrics for a low-risk individual."""
    return {
        "age": 25,
        "gender": "female",
        "bmi": 22.0,
        "hba1c": 5.0,
        "fasting_glucose": 85,
        "total_cholesterol": 170,
        "hdl_cholesterol": 65,
        "waist_circumference": 70,
        "smoking_status": "never",
        "family_diabetes": False
    }


@pytest.fixture
def minimal_metrics():
    """Minimum required metrics (just age and gender)."""
    return {
        "age": 40,
        "gender": "female"
    }