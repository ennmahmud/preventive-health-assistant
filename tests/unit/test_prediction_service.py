"""
Test Prediction Service
=======================
Unit tests for the prediction service.
"""

import pytest
import pandas as pd

from src.api.services.prediction_service import PredictionService, prediction_service


class TestPredictionService:
    """Tests for PredictionService class."""

    def test_service_is_ready_after_model_load(self):
        """Test service reports ready after model is loaded."""
        # Model is loaded by the conftest fixture
        assert prediction_service.is_ready() == True

    def test_model_version_is_set(self):
        """Test model version is extracted from filename."""
        assert prediction_service.model_version != "unknown"
        assert len(prediction_service.model_version) > 0


class TestFeaturePreparation:
    """Tests for feature preparation logic."""

    def test_prepare_features_minimal(self, minimal_metrics):
        """Test feature preparation with minimal inputs."""
        features_df = prediction_service.prepare_features(minimal_metrics)

        assert isinstance(features_df, pd.DataFrame)
        assert len(features_df) == 1  # One row
        assert features_df['age'].iloc[0] == 40

    def test_prepare_features_full(self, sample_metrics):
        """Test feature preparation with full inputs."""
        features_df = prediction_service.prepare_features(sample_metrics)

        assert features_df['age'].iloc[0] == 45
        assert features_df['bmi'].iloc[0] == 28.5
        assert features_df['hba1c'].iloc[0] == 5.7

    def test_gender_encoding(self):
        """Test gender is encoded correctly."""
        # Model uses: 0=Male, 1=Female (from NHANES encoding)
        male_features = prediction_service.prepare_features({"age": 30, "gender": "male"})
        female_features = prediction_service.prepare_features({"age": 30, "gender": "female"})

        assert male_features['gender'].iloc[0] == 0
        assert female_features['gender'].iloc[0] == 1

    def test_age_group_encoding(self):
        """Test age groups are one-hot encoded correctly."""
        # Model uses drop_first=True, so '18-35' is reference category (all zeros)
        # One-hot columns: age_group_36-45, age_group_46-55, age_group_56-65, age_group_65+
        young = prediction_service.prepare_features({"age": 25, "gender": "male"})
        middle = prediction_service.prepare_features({"age": 40, "gender": "male"})
        older = prediction_service.prepare_features({"age": 50, "gender": "male"})
        senior = prediction_service.prepare_features({"age": 70, "gender": "male"})

        # Young (18-35) is reference: all age_group columns should be 0
        assert young['age_group_36-45'].iloc[0] == 0
        assert young['age_group_65+'].iloc[0] == 0
        # Middle (36-45) should have age_group_36-45 = 1
        assert middle['age_group_36-45'].iloc[0] == 1
        # Older (46-55) should have age_group_46-55 = 1
        assert older['age_group_46-55'].iloc[0] == 1
        # Senior (65+) should have age_group_65+ = 1
        assert senior['age_group_65+'].iloc[0] == 1

    def test_bmi_category_encoding(self):
        """Test BMI categories are one-hot encoded correctly."""
        # Model uses drop_first=True, so 'Normal' is reference category (all zeros for these columns)
        # One-hot columns: bmi_category_Obese_I, bmi_category_Obese_II, bmi_category_Obese_III,
        #                  bmi_category_Overweight, bmi_category_Underweight
        underweight = prediction_service.prepare_features({"age": 30, "gender": "male", "bmi": 17})
        normal = prediction_service.prepare_features({"age": 30, "gender": "male", "bmi": 22})
        overweight = prediction_service.prepare_features({"age": 30, "gender": "male", "bmi": 27})
        obese = prediction_service.prepare_features({"age": 30, "gender": "male", "bmi": 32})

        assert underweight['bmi_category_Underweight'].iloc[0] == 1
        # Normal is reference category - all BMI category columns should be 0
        assert normal['bmi_category_Underweight'].iloc[0] == 0
        assert normal['bmi_category_Overweight'].iloc[0] == 0
        assert normal['bmi_category_Obese_I'].iloc[0] == 0
        assert overweight['bmi_category_Overweight'].iloc[0] == 1
        assert obese['bmi_category_Obese_I'].iloc[0] == 1

    def test_missing_values_get_defaults(self, minimal_metrics):
        """Test missing values are filled with defaults."""
        features_df = prediction_service.prepare_features(minimal_metrics)

        # Should have default values, not NaN
        assert pd.notna(features_df['bmi'].iloc[0])
        assert pd.notna(features_df['hba1c'].iloc[0])
        assert pd.notna(features_df['fasting_glucose'].iloc[0])

    def test_smoking_status_encoding(self):
        """Test smoking status is encoded correctly."""
        never = prediction_service.prepare_features({"age": 30, "gender": "male", "smoking_status": "never"})
        former = prediction_service.prepare_features({"age": 30, "gender": "male", "smoking_status": "former"})
        current = prediction_service.prepare_features({"age": 30, "gender": "male", "smoking_status": "current"})

        assert never['current_smoker'].iloc[0] == 0
        assert former['current_smoker'].iloc[0] == 0
        assert current['current_smoker'].iloc[0] == 1

    def test_feature_order_matches_model(self, sample_metrics):
        """Test features are ordered to match model expectations."""
        features_df = prediction_service.prepare_features(sample_metrics)

        if prediction_service.model and prediction_service.model.feature_names:
            assert list(features_df.columns) == prediction_service.model.feature_names


class TestPredictions:
    """Tests for prediction functionality."""

    def test_predict_returns_required_fields(self, sample_metrics):
        """Test prediction returns all required fields."""
        result = prediction_service.predict(sample_metrics, include_explanation=False)

        assert 'assessment_id' in result
        assert 'timestamp' in result
        assert 'risk' in result
        assert 'model_version' in result

        risk = result['risk']
        assert 'risk_probability' in risk
        assert 'risk_percentage' in risk
        assert 'risk_category' in risk
        assert 'prediction' in risk
        assert 'confidence' in risk

    def test_risk_probability_range(self, sample_metrics):
        """Test risk probability is between 0 and 1."""
        result = prediction_service.predict(sample_metrics, include_explanation=False)

        assert 0 <= result['risk']['risk_probability'] <= 1

    def test_risk_percentage_matches_probability(self, sample_metrics):
        """Test risk percentage is probability * 100."""
        result = prediction_service.predict(sample_metrics, include_explanation=False)

        expected_percentage = result['risk']['risk_probability'] * 100
        assert abs(result['risk']['risk_percentage'] - expected_percentage) < 0.1

    def test_high_risk_individual(self, high_risk_metrics):
        """Test high-risk individual gets elevated risk."""
        result = prediction_service.predict(high_risk_metrics, include_explanation=False)

        # With HbA1c of 6.8, they should be high risk
        assert result['risk']['risk_category'] in ['High', 'Very High']
        assert result['risk']['risk_probability'] > 0.4

    def test_low_risk_individual(self, low_risk_metrics):
        """Test low-risk individual gets low risk."""
        result = prediction_service.predict(low_risk_metrics, include_explanation=False)

        # Young, healthy individual should be low risk
        assert result['risk']['risk_category'] in ['Low', 'Moderate']
        assert result['risk']['risk_probability'] < 0.4

    def test_prediction_with_explanation(self, sample_metrics):
        """Test prediction includes explanation when requested."""
        result = prediction_service.predict(sample_metrics, include_explanation=True)

        assert 'explanation' in result
        assert result['explanation'] is not None

        explanation = result['explanation']
        assert 'base_risk' in explanation
        # SHAP explainer returns 'top_risk_factors' and 'top_protective_factors'
        assert 'top_risk_factors' in explanation
        assert 'top_protective_factors' in explanation
        assert 'all_contributions' in explanation

    def test_prediction_without_explanation(self, sample_metrics):
        """Test prediction excludes explanation when not requested."""
        result = prediction_service.predict(sample_metrics, include_explanation=False)

        assert 'explanation' not in result or result.get('explanation') is None

    def test_assessment_id_is_unique(self, sample_metrics):
        """Test each prediction gets a unique assessment ID."""
        result1 = prediction_service.predict(sample_metrics, include_explanation=False)
        result2 = prediction_service.predict(sample_metrics, include_explanation=False)

        assert result1['assessment_id'] != result2['assessment_id']


class TestRecommendations:
    """Tests for recommendation generation."""

    def test_recommendations_for_high_bmi(self, sample_metrics):
        """Test weight recommendation for high BMI."""
        metrics = {**sample_metrics, 'bmi': 32.0}
        result = prediction_service.predict(metrics, include_explanation=False)
        recs = prediction_service.generate_recommendations(metrics, result)

        weight_recs = [r for r in recs if r['category'] == 'weight']
        assert len(weight_recs) > 0
        assert weight_recs[0]['priority'] == 'high'  # BMI >= 30 is high priority

    def test_recommendations_for_elevated_hba1c(self, sample_metrics):
        """Test blood sugar recommendation for elevated HbA1c."""
        metrics = {**sample_metrics, 'hba1c': 6.0}
        result = prediction_service.predict(metrics, include_explanation=False)
        recs = prediction_service.generate_recommendations(metrics, result)

        sugar_recs = [r for r in recs if r['category'] == 'blood_sugar']
        assert len(sugar_recs) > 0

    def test_recommendations_for_smoker(self, sample_metrics):
        """Test smoking cessation recommendation for current smokers."""
        metrics = {**sample_metrics, 'smoking_status': 'current'}
        result = prediction_service.predict(metrics, include_explanation=False)
        recs = prediction_service.generate_recommendations(metrics, result)

        smoking_recs = [r for r in recs if r['category'] == 'lifestyle']
        assert len(smoking_recs) > 0
        assert smoking_recs[0]['priority'] == 'high'

    def test_recommendations_have_sources(self, high_risk_metrics):
        """Test recommendations include evidence sources."""
        result = prediction_service.predict(high_risk_metrics, include_explanation=False)
        recs = prediction_service.generate_recommendations(high_risk_metrics, result)

        # At least some recommendations should have sources
        recs_with_sources = [r for r in recs if r.get('source')]
        assert len(recs_with_sources) > 0


class TestModelInfo:
    """Tests for model info endpoint."""

    def test_get_model_info(self):
        """Test getting model information."""
        info = prediction_service.get_model_info()

        assert 'model_name' in info
        assert 'version' in info
        assert 'n_features' in info
        assert 'feature_names' in info
        assert 'performance_metrics' in info

    def test_model_info_metrics(self):
        """Test model info includes performance metrics."""
        info = prediction_service.get_model_info()
        metrics = info['performance_metrics']

        assert 'accuracy' in metrics
        assert 'roc_auc' in metrics
        assert metrics['accuracy'] > 0.9  # We achieved 94.85%
        assert metrics['roc_auc'] > 0.9  # We achieved 96.75%