"""
Test ML Model
=============
Tests for the diabetes risk prediction model.
"""

import sys
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.ml.models import DiabetesRiskModel
from config import MODELS_DIR


class TestDiabetesRiskModel:
    """Tests for DiabetesRiskModel class."""

    @pytest.fixture
    def model(self):
        """Load the trained model."""
        model_path = list((MODELS_DIR / "saved").glob("diabetes_model_*.joblib"))[0]
        return DiabetesRiskModel.load(model_path)

    def test_model_loads_successfully(self, model):
        """Test model loads without errors."""
        assert model is not None
        assert model._is_fitted == True

    def test_model_has_feature_names(self, model):
        """Test model has feature names stored."""
        assert len(model.feature_names) > 0
        assert 'age' in model.feature_names
        assert 'bmi' in model.feature_names

    def test_model_has_metadata(self, model):
        """Test model has training metadata."""
        assert 'trained_at' in model.metadata
        assert 'n_samples' in model.metadata
        assert 'n_features' in model.metadata

    def test_predict_returns_binary(self, model):
        """Test predict returns binary values."""
        # Create dummy input matching model features
        X = pd.DataFrame([{f: 0 for f in model.feature_names}])
        X['age'] = 45
        X['bmi'] = 28

        predictions = model.predict(X)

        assert len(predictions) == 1
        assert predictions[0] in [0, 1]

    def test_predict_proba_returns_probabilities(self, model):
        """Test predict_proba returns valid probabilities."""
        X = pd.DataFrame([{f: 0 for f in model.feature_names}])
        X['age'] = 45
        X['bmi'] = 28

        probabilities = model.predict_proba(X)

        assert probabilities.shape == (1, 2)
        assert 0 <= probabilities[0, 0] <= 1
        assert 0 <= probabilities[0, 1] <= 1
        assert abs(probabilities[0, 0] + probabilities[0, 1] - 1.0) < 0.001

    def test_predict_risk_returns_dataframe(self, model):
        """Test predict_risk returns a DataFrame with risk info."""
        X = pd.DataFrame([{f: 0 for f in model.feature_names}])
        X['age'] = 45
        X['bmi'] = 28

        risk_df = model.predict_risk(X)

        assert isinstance(risk_df, pd.DataFrame)
        assert 'risk_probability' in risk_df.columns
        assert 'risk_percentage' in risk_df.columns
        assert 'risk_category' in risk_df.columns
        assert 'prediction' in risk_df.columns

    def test_risk_category_assignment(self, model):
        """Test risk categories are assigned correctly."""
        # Create inputs that should give different risk levels
        X = pd.DataFrame([{f: 0 for f in model.feature_names} for _ in range(4)])

        risk_df = model.predict_risk(X)

        # All categories should be valid
        valid_categories = ['Low', 'Moderate', 'High', 'Very High']
        for cat in risk_df['risk_category']:
            assert cat in valid_categories

    def test_feature_importance(self, model):
        """Test feature importance extraction."""
        importance_df = model.get_feature_importance()

        assert isinstance(importance_df, pd.DataFrame)
        assert 'feature' in importance_df.columns
        assert 'importance' in importance_df.columns
        assert len(importance_df) > 0

        # Should be sorted by importance
        assert importance_df['importance'].iloc[0] >= importance_df['importance'].iloc[-1]

    def test_get_params(self, model):
        """Test getting model parameters."""
        params = model.get_params()

        assert 'n_estimators' in params
        assert 'max_depth' in params
        assert 'learning_rate' in params


# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ml.models.diabetes_model import DiabetesRiskModel

MODELS_DIR = PROJECT_ROOT / "models"

@pytest.fixture
def model():
    """Load the trained model or skip tests if not available"""
    model_files = list((MODELS_DIR / "saved").glob("diabetes_model_*.joblib"))

    if not model_files:
        pytest.skip("No trained model found. Run training first: python scripts/train_model.py")

    model_path = model_files[0]
    return DiabetesRiskModel.load(model_path)