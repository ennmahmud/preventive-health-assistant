"""
Diabetes Risk Model
===================
XGBoost-based model for predicting diabetes risk.

This model is trained on NHANES data and provides:
- Binary classification (diabetes/no diabetes)
- Probability estimates for risk assessment
- Feature importance for explainability
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import StratifiedKFold, cross_val_score

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config import DIABETES_CONFIG, MODELS_DIR

logger = logging.getLogger(__name__)


class DiabetesRiskModel(BaseEstimator, ClassifierMixin):
    """
    XGBoost classifier for diabetes risk prediction.

    This model wraps XGBoost with additional functionality for:
    - Standardized training with cross-validation
    - Model persistence and versioning
    - Feature importance extraction
    - Prediction with confidence intervals

    Attributes:
        model: Underlying XGBoost classifier
        feature_names: List of feature names used in training
        metadata: Training metadata (date, metrics, parameters)

    Example:
        >>> model = DiabetesRiskModel()
        >>> model.fit(X_train, y_train)
        >>> predictions = model.predict(X_test)
        >>> probabilities = model.predict_proba(X_test)
    """

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
        early_stopping_rounds: int = 20,
        **kwargs,
    ):
        """
        Initialize the diabetes risk model.

        Args:
            n_estimators: Number of boosting rounds
            max_depth: Maximum tree depth
            learning_rate: Boosting learning rate
            subsample: Subsample ratio of training instances
            colsample_bytree: Subsample ratio of columns per tree
            random_state: Random seed for reproducibility
            early_stopping_rounds: Stop if no improvement for this many rounds
            **kwargs: Additional XGBoost parameters
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state = random_state
        self.early_stopping_rounds = early_stopping_rounds
        self.kwargs = kwargs

        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_names: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self._is_fitted = False

    def _create_model(self) -> xgb.XGBClassifier:
        """Create XGBoost classifier with configured parameters."""
        return xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state,
            eval_metric="auc",
            use_label_encoder=False,
            verbosity=1,
            **self.kwargs,
        )

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        eval_set: Optional[List[Tuple[pd.DataFrame, pd.Series]]] = None,
        verbose: bool = True,
    ) -> "DiabetesRiskModel":
        """
        Train the diabetes risk model.

        Args:
            X: Training features
            y: Training labels
            eval_set: Optional validation set for early stopping
            verbose: Whether to print training progress

        Returns:
            self: Fitted model
        """
        logger.info(f"Training diabetes model on {len(X)} samples with {len(X.columns)} features")

        # Store feature names
        self.feature_names = list(X.columns)

        # Create model with early_stopping_rounds in constructor
        self.model = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state,
            eval_metric="auc",
            early_stopping_rounds=self.early_stopping_rounds if eval_set else None,
            verbosity=1 if verbose else 0,
            **self.kwargs,
        )

        # Train
        if eval_set:
            self.model.fit(X, y, eval_set=eval_set, verbose=verbose)
        else:
            self.model.fit(X, y)

        # Store metadata
        self.metadata = {
            "trained_at": datetime.now().isoformat(),
            "n_samples": len(X),
            "n_features": len(self.feature_names),
            "feature_names": self.feature_names,
            "params": self.get_params(),
            "best_iteration": getattr(self.model, "best_iteration", self.n_estimators),
        }

        self._is_fitted = True
        logger.info(f"Training complete. Best iteration: {self.metadata['best_iteration']}")

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict diabetes status.

        Args:
            X: Features to predict on

        Returns:
            Binary predictions (0 or 1)
        """
        self._check_is_fitted()
        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict diabetes probability.

        Args:
            X: Features to predict on

        Returns:
            Probability estimates [P(no diabetes), P(diabetes)]
        """
        self._check_is_fitted()
        return self.model.predict_proba(X)

    def predict_risk(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Predict diabetes risk with additional context.

        Returns a DataFrame with:
        - risk_probability: Probability of diabetes (0-1)
        - risk_category: Low/Moderate/High/Very High
        - prediction: Binary prediction

        Args:
            X: Features to predict on

        Returns:
            DataFrame with risk assessment
        """
        self._check_is_fitted()

        proba = self.predict_proba(X)[:, 1]
        predictions = self.predict(X)

        # Categorize risk
        def categorize_risk(p: float) -> str:
            if p < 0.2:
                return "Low"
            elif p < 0.4:
                return "Moderate"
            elif p < 0.6:
                return "High"
            else:
                return "Very High"

        risk_df = pd.DataFrame(
            {
                "risk_probability": proba,
                "risk_percentage": (proba * 100).round(1),
                "risk_category": [categorize_risk(p) for p in proba],
                "prediction": predictions,
            }
        )

        return risk_df

    def get_feature_importance(self, importance_type: str = "gain") -> pd.DataFrame:
        """
        Get feature importance scores.

        Args:
            importance_type: Type of importance ('gain', 'weight', 'cover')

        Returns:
            DataFrame with feature names and importance scores, sorted by importance
        """
        self._check_is_fitted()

        # Get feature importance directly from the model
        importance = self.model.feature_importances_

        importance_df = pd.DataFrame({"feature": self.feature_names, "importance": importance})

        # Normalize to percentages
        importance_df["importance_pct"] = (
            100 * importance_df["importance"] / importance_df["importance"].sum()
        ).round(2)

        return importance_df.sort_values("importance", ascending=False).reset_index(drop=True)

    def cross_validate(
        self, X: pd.DataFrame, y: pd.Series, cv: int = 5, scoring: List[str] = None
    ) -> Dict[str, np.ndarray]:
        """
        Perform cross-validation.

        Args:
            X: Features
            y: Labels
            cv: Number of folds
            scoring: Scoring metrics to compute

        Returns:
            Dictionary of metric name -> array of scores
        """
        if scoring is None:
            scoring = ["accuracy", "roc_auc", "precision", "recall", "f1"]

        logger.info(f"Running {cv}-fold cross-validation")

        results = {}
        cv_splitter = StratifiedKFold(n_splits=cv, shuffle=True, random_state=self.random_state)

        for metric in scoring:
            scores = cross_val_score(self._create_model(), X, y, cv=cv_splitter, scoring=metric)
            results[metric] = scores
            logger.info(f"  {metric}: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")

        return results

    def save(self, path: Optional[Path] = None, version: Optional[str] = None) -> Path:
        """
        Save model to disk.

        Args:
            path: Directory to save to. Defaults to models/saved
            version: Version string. Defaults to timestamp

        Returns:
            Path to saved model file
        """
        self._check_is_fitted()

        path = path or MODELS_DIR
        path.mkdir(parents=True, exist_ok=True)

        version = version or datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"diabetes_model_{version}.joblib"
        filepath = path / filename

        # Save model and metadata together
        save_data = {
            "model": self.model,
            "feature_names": self.feature_names,
            "metadata": self.metadata,
            "params": self.get_params(),
        }

        joblib.dump(save_data, filepath)

        # Also save metadata as JSON for easy inspection
        metadata_path = path / f"diabetes_model_{version}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2, default=str)

        logger.info(f"Model saved to {filepath}")

        return filepath

    @classmethod
    def load(cls, filepath: Path) -> "DiabetesRiskModel":
        """
        Load model from disk.

        Args:
            filepath: Path to saved model file

        Returns:
            Loaded DiabetesRiskModel instance
        """
        logger.info(f"Loading model from {filepath}")

        save_data = joblib.load(filepath)

        # Create instance with saved parameters
        instance = cls(**save_data["params"])
        instance.model = save_data["model"]
        instance.feature_names = save_data["feature_names"]
        instance.metadata = save_data["metadata"]
        instance._is_fitted = True

        return instance

    def _check_is_fitted(self):
        """Check if model has been fitted."""
        if not self._is_fitted:
            raise ValueError("Model has not been fitted. Call fit() first.")

    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        """Get model parameters."""
        return {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "random_state": self.random_state,
            "early_stopping_rounds": self.early_stopping_rounds,
            **self.kwargs,
        }

    def set_params(self, **params) -> "DiabetesRiskModel":
        """Set model parameters."""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.kwargs[key] = value
        return self


def main():
    """Demo of the diabetes risk model."""
    print("\nDiabetes Risk Model - Ready")
    print("Usage:")
    print("  model = DiabetesRiskModel()")
    print("  model.fit(X_train, y_train)")
    print("  risk_assessment = model.predict_risk(X_new)")


if __name__ == "__main__":
    main()
