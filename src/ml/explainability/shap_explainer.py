"""
SHAP Explainability
===================
Explainable AI using SHAP (SHapley Additive exPlanations) for health risk models.

Provides:
- Individual prediction explanations (why did this person get this risk score?)
- Global feature importance (what factors matter most overall?)
- Feature interaction analysis
- Visualization helpers for clinical communication
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging

import numpy as np
import pandas as pd
import shap

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

logger = logging.getLogger(__name__)


class SHAPExplainer:
    """
    SHAP-based model explainability for health risk predictions.
    
    SHAP values show how each feature contributes to pushing the prediction
    away from the baseline (average prediction). This is critical for:
    - Clinical transparency: Explaining why a patient has a certain risk level
    - Trust: Allowing healthcare providers to verify model reasoning
    - Actionable insights: Identifying modifiable risk factors
    
    Example:
        >>> explainer = SHAPExplainer(model)
        >>> explanation = explainer.explain_prediction(patient_data)
        >>> print(explanation['top_risk_factors'])
    """
    
    def __init__(
        self,
        model: Any,
        feature_names: Optional[List[str]] = None,
        background_data: Optional[pd.DataFrame] = None
    ):
        """
        Initialize SHAP explainer.
        
        Args:
            model: Trained model (XGBoost, sklearn, etc.)
            feature_names: List of feature names
            background_data: Background dataset for SHAP calculations
        """
        self.model = model
        self.feature_names = feature_names or []
        self.background_data = background_data
        self.explainer: Optional[shap.Explainer] = None
        self._is_initialized = False
    
    def initialize(self, background_data: Optional[pd.DataFrame] = None) -> None:
        """
        Initialize the SHAP explainer with background data.
        
        For tree-based models, uses TreeExplainer for efficiency.
        
        Args:
            background_data: Background dataset (uses stored if not provided)
        """
        if background_data is not None:
            self.background_data = background_data
        
        if self.background_data is None:
            raise ValueError("Background data required for initialization")
        
        logger.info("Initializing SHAP explainer...")
        
        # Use TreeExplainer for XGBoost (much faster)
        try:
            self.explainer = shap.TreeExplainer(self.model)
            logger.info("Using TreeExplainer for tree-based model")
        except Exception:
            # Fall back to KernelExplainer for other model types
            logger.info("Using KernelExplainer")
            self.explainer = shap.KernelExplainer(
                self.model.predict_proba,
                shap.sample(self.background_data, 100)
            )
        
        # Update feature names if available from background data
        if not self.feature_names and hasattr(self.background_data, 'columns'):
            self.feature_names = list(self.background_data.columns)
        
        self._is_initialized = True
        logger.info("SHAP explainer initialized successfully")
    
    def compute_shap_values(
        self,
        X: pd.DataFrame,
        check_additivity: bool = False
    ) -> np.ndarray:
        """
        Compute SHAP values for given data.
        
        Args:
            X: Data to explain
            check_additivity: Whether to verify SHAP additivity property
            
        Returns:
            SHAP values array
        """
        self._check_initialized()
        
        shap_values = self.explainer.shap_values(X, check_additivity=check_additivity)
        
        # For binary classification, get values for positive class
        if isinstance(shap_values, list) and len(shap_values) == 2:
            shap_values = shap_values[1]
        
        return shap_values
    
    def explain_prediction(
        self,
        X: pd.DataFrame,
        index: int = 0,
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Generate human-readable explanation for a single prediction.
        
        Args:
            X: Input data (can be multiple rows)
            index: Which row to explain (default: first)
            top_n: Number of top factors to highlight
            
        Returns:
            Dictionary with explanation components
        """
        self._check_initialized()
        
        # Get single instance
        if len(X) > 1:
            instance = X.iloc[[index]]
        else:
            instance = X
        
        # Compute SHAP values
        shap_values = self.compute_shap_values(instance)
        if len(shap_values.shape) > 1:
            shap_values = shap_values[0]
        
        # Get feature values
        feature_values = instance.iloc[0].to_dict()
        
        # Create feature contributions
        contributions = []
        for i, (feature, shap_val) in enumerate(zip(self.feature_names, shap_values)):
            contributions.append({
                'feature': feature,
                'value': feature_values.get(feature, None),
                'shap_value': float(shap_val),
                'direction': 'increases' if shap_val > 0 else 'decreases',
                'impact': 'risk' if shap_val > 0 else 'protection'
            })
        
        # Sort by absolute SHAP value
        contributions.sort(key=lambda x: abs(x['shap_value']), reverse=True)
        
        # Get base value (expected value)
        base_value = float(self.explainer.expected_value)
        if isinstance(self.explainer.expected_value, np.ndarray):
            base_value = float(self.explainer.expected_value[1])  # Positive class
        
        # Calculate final prediction contribution
        total_shap = sum(c['shap_value'] for c in contributions)
        
        explanation = {
            'base_risk': base_value,
            'total_contribution': total_shap,
            'predicted_risk': base_value + total_shap,
            'top_risk_factors': [c for c in contributions[:top_n] if c['shap_value'] > 0],
            'top_protective_factors': [c for c in contributions[:top_n] if c['shap_value'] < 0],
            'all_contributions': contributions,
            'feature_values': feature_values
        }
        
        return explanation
    
    def generate_text_explanation(
        self,
        explanation: Dict[str, Any],
        patient_friendly: bool = True
    ) -> str:
        """
        Generate natural language explanation from SHAP analysis.
        
        Args:
            explanation: Output from explain_prediction()
            patient_friendly: If True, use simpler language
            
        Returns:
            Human-readable explanation string
        """
        lines = []
        
        # Overall risk
        risk_pct = explanation['predicted_risk'] * 100
        if risk_pct < 20:
            risk_level = "low"
        elif risk_pct < 40:
            risk_level = "moderate"
        elif risk_pct < 60:
            risk_level = "elevated"
        else:
            risk_level = "high"
        
        lines.append(f"Based on the assessment, the estimated diabetes risk is {risk_level} ({risk_pct:.1f}%).")
        lines.append("")
        
        # Risk factors
        risk_factors = explanation['top_risk_factors']
        if risk_factors:
            lines.append("Key factors contributing to increased risk:")
            for factor in risk_factors[:3]:
                feature_name = self._format_feature_name(factor['feature'], patient_friendly)
                value = self._format_feature_value(factor['feature'], factor['value'])
                lines.append(f"  • {feature_name}: {value}")
        
        # Protective factors
        protective = explanation['top_protective_factors']
        if protective:
            lines.append("")
            lines.append("Factors that lower risk:")
            for factor in protective[:3]:
                feature_name = self._format_feature_name(factor['feature'], patient_friendly)
                value = self._format_feature_value(factor['feature'], factor['value'])
                lines.append(f"  • {feature_name}: {value}")
        
        return "\n".join(lines)
    
    def _format_feature_name(self, feature: str, patient_friendly: bool) -> str:
        """Convert technical feature names to readable format."""
        if not patient_friendly:
            return feature
        
        # Mapping of technical names to friendly names
        friendly_names = {
            'bmi': 'Body Mass Index (BMI)',
            'age': 'Age',
            'hba1c': 'Blood sugar level (HbA1c)',
            'fasting_glucose': 'Fasting blood glucose',
            'systolic_bp': 'Blood pressure (systolic)',
            'diastolic_bp': 'Blood pressure (diastolic)',
            'total_cholesterol': 'Total cholesterol',
            'hdl_cholesterol': 'HDL (good) cholesterol',
            'waist_circumference': 'Waist circumference',
            'family_diabetes': 'Family history of diabetes',
            'hypertension': 'High blood pressure',
            'smoking_status_Current': 'Current smoking',
            'smoking_status_Former': 'Former smoking',
            'activity_level_Sedentary': 'Low physical activity',
            'gender': 'Gender',
        }
        
        return friendly_names.get(feature, feature.replace('_', ' ').title())
    
    def _format_feature_value(self, feature: str, value: Any) -> str:
        """Format feature value for display."""
        if value is None:
            return "Unknown"
        
        # Format based on feature type
        if feature == 'bmi':
            return f"{value:.1f} kg/m²"
        elif feature == 'age':
            return f"{int(value)} years"
        elif feature in ['hba1c']:
            return f"{value:.1f}%"
        elif feature in ['fasting_glucose', 'total_cholesterol', 'hdl_cholesterol']:
            return f"{value:.0f} mg/dL"
        elif feature in ['systolic_bp', 'diastolic_bp']:
            return f"{value:.0f} mmHg"
        elif feature == 'waist_circumference':
            return f"{value:.1f} cm"
        elif feature == 'gender':
            return "Female" if value == 1 else "Male"
        elif value in [0, 1]:
            return "Yes" if value == 1 else "No"
        else:
            return str(value)
    
    def get_global_importance(
        self,
        X: pd.DataFrame,
        max_samples: int = 1000
    ) -> pd.DataFrame:
        """
        Compute global feature importance using mean absolute SHAP values.
        
        Args:
            X: Dataset to compute importance on
            max_samples: Maximum samples to use (for efficiency)
            
        Returns:
            DataFrame with features sorted by importance
        """
        self._check_initialized()
        
        # Sample if too large
        if len(X) > max_samples:
            X = X.sample(n=max_samples, random_state=42)
        
        logger.info(f"Computing global SHAP importance on {len(X)} samples...")
        
        shap_values = self.compute_shap_values(X)
        
        # Mean absolute SHAP value per feature
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'mean_abs_shap': mean_abs_shap,
            'importance_pct': 100 * mean_abs_shap / mean_abs_shap.sum()
        }).sort_values('mean_abs_shap', ascending=False).reset_index(drop=True)
        
        return importance_df
    
    def _check_initialized(self):
        """Check if explainer has been initialized."""
        if not self._is_initialized:
            raise ValueError("Explainer not initialized. Call initialize() first.")


def main():
    """Demo of SHAP explainability."""
    print("\nSHAP Explainer - Ready")
    print("Usage:")
    print("  explainer = SHAPExplainer(model)")
    print("  explainer.initialize(X_train)")
    print("  explanation = explainer.explain_prediction(X_new)")
    print("  print(explainer.generate_text_explanation(explanation))")


if __name__ == "__main__":
    main()
