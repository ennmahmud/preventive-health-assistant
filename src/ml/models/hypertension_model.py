"""
Hypertension Risk Model
=======================
XGBoost-based model for predicting hypertension risk.

Trained on NHANES data.  Target: measured hypertension (systolic BP >= 140
or diastolic BP >= 90).  Blood pressure readings are deliberately excluded
from the feature set so the model can be applied preventively — i.e. to
patients who do not yet know their blood pressure.
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

from config import HYPERTENSION_CONFIG, MODELS_DIR

logger = logging.getLogger(__name__)


class HypertensionRiskModel(BaseEstimator, ClassifierMixin):
    """
    XGBoost classifier for hypertension risk prediction.

    Predicts whether a person is at risk of hypertension from lifestyle and
    demographic factors, WITHOUT requiring blood pressure readings as input.

    Example:
        >>> model = HypertensionRiskModel()
        >>> model.fit(X_train, y_train)
        >>> risk_df = model.predict_risk(X_new)
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
        """Create a fresh XGBoost classifier with configured parameters."""
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
    ) -> "HypertensionRiskModel":
        """
        Train the hypertension risk model.

        Args:
            X: Training features (must NOT include raw BP readings)
            y: Training labels (1 = hypertensive, 0 = normotensive)
            eval_set: Optional validation set for early stopping
            verbose: Whether to print training progress

        Returns:
            self: Fitted model
        """
        logger.info(
            f"Training hypertension model on {len(X)} samples with {len(X.columns)} features"
        )

        self.feature_names = list(X.columns)

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

        if eval_set:
            self.model.fit(X, y, eval_set=eval_set, verbose=verbose)
        else:
            self.model.fit(X, y)

        self.metadata = {
            "trained_at": datetime.now().isoformat(),
            "n_samples": len(X),
            "n_features": len(self.feature_names),
            "feature_names": self.feature_names,
            "params": self.get_params(),
            "best_iteration": getattr(self.model, "best_iteration", self.n_estimators),
            "model_type": "Hypertension Risk Model",
            "note": "BP readings excluded from features — preventive risk model",
        }

        self._is_fitted = True
        logger.info(
            f"Hypertension training complete. Best iteration: {self.metadata['best_iteration']}"
        )
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return binary hypertension predictions (0 or 1)."""
        self._check_is_fitted()
        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return probability estimates [P(normotensive), P(hypertensive)]."""
        self._check_is_fitted()
        return self.model.predict_proba(X)

    def predict_risk(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Predict hypertension risk with risk categorisation.

        Thresholds reflect the population prevalence and clinical staging:
          Low      < 15%   — unlikely to have elevated BP
          Moderate 15-30%  — borderline / Stage 1 risk
          High     30-50%  — elevated risk, lifestyle changes recommended
          Very High >= 50% — high probability, medical screening recommended

        Returns:
            DataFrame with columns: risk_probability, risk_percentage,
                                    risk_category, prediction
        """
        self._check_is_fitted()

        proba = self.predict_proba(X)[:, 1]
        predictions = self.predict(X)

        def categorize_risk(p: float) -> str:
            if p < 0.15:
                return "Low"
            elif p < 0.30:
                return "Moderate"
            elif p < 0.50:
                return "High"
            else:
                return "Very High"

        return pd.DataFrame(
            {
                "risk_probability": proba,
                "risk_percentage": (proba * 100).round(1),
                "risk_category": [categorize_risk(p) for p in proba],
                "prediction": predictions,
            }
        )

    def get_feature_importance(self, importance_type: str = "gain") -> pd.DataFrame:
        """
        Return feature importance scores sorted by importance.

        Args:
            importance_type: 'gain', 'weight', or 'cover'

        Returns:
            DataFrame with columns: feature, importance, importance_pct
        """
        self._check_is_fitted()
        importance = self.model.feature_importances_
        df = pd.DataFrame({"feature": self.feature_names, "importance": importance})
        df["importance_pct"] = (100 * df["importance"] / df["importance"].sum()).round(2)
        return df.sort_values("importance", ascending=False).reset_index(drop=True)

    def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv: int = 5,
        scoring: Optional[List[str]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Perform stratified k-fold cross-validation.

        Args:
            X: Features
            y: Labels
            cv: Number of folds
            scoring: Metrics to compute

        Returns:
            Dict mapping metric name → array of scores
        """
        if scoring is None:
            scoring = ["accuracy", "roc_auc", "precision", "recall", "f1"]

        logger.info(f"Running {cv}-fold CV on hypertension model")
        cv_splitter = StratifiedKFold(n_splits=cv, shuffle=True, random_state=self.random_state)

        results = {}
        for metric in scoring:
            scores = cross_val_score(
                self._create_model(), X, y, cv=cv_splitter, scoring=metric
            )
            results[metric] = scores
            logger.info(f"  {metric}: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")

        return results

    def save(self, path: Optional[Path] = None, version: Optional[str] = None) -> Path:
        """
        Save model and metadata to disk.

        Args:
            path: Directory for saving. Defaults to models/saved
            version: Version string. Defaults to timestamp.

        Returns:
            Path to saved .joblib file
        """
        self._check_is_fitted()

        path = path or MODELS_DIR
        path.mkdir(parents=True, exist_ok=True)

        version = version or datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hypertension_model_{version}.joblib"
        filepath = path / filename

        save_data = {
            "model": self.model,
            "feature_names": self.feature_names,
            "metadata": self.metadata,
            "params": self.get_params(),
        }
        joblib.dump(save_data, filepath)

        metadata_path = path / f"hypertension_model_{version}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2, default=str)

        logger.info(f"Hypertension model saved to {filepath}")
        return filepath

    @classmethod
    def load(cls, filepath: Path) -> "HypertensionRiskModel":
        """
        Load model from disk.

        Args:
            filepath: Path to .joblib file

        Returns:
            Loaded HypertensionRiskModel instance
        """
        logger.info(f"Loading hypertension model from {filepath}")
        save_data = joblib.load(filepath)

        instance = cls(**save_data["params"])
        instance.model = save_data["model"]
        instance.feature_names = save_data["feature_names"]
        instance.metadata = save_data["metadata"]
        instance._is_fitted = True
        return instance

    def _check_is_fitted(self):
        """Raise ValueError if model hasn't been trained."""
        if not self._is_fitted:
            raise ValueError(
                "HypertensionRiskModel has not been fitted. Call fit() first."
            )

    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        """Return model hyperparameters."""
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

    def set_params(self, **params) -> "HypertensionRiskModel":
        """Set model hyperparameters."""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.kwargs[key] = value
        return self


def main():
    print("\nHypertension Risk Model — Ready")
    print("Usage:")
    print("  model = HypertensionRiskModel()")
    print("  model.fit(X_train, y_train)")
    print("  risk_df = model.predict_risk(X_new)")


if __name__ == "__main__":
    main()
