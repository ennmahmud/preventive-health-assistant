"""
Model Evaluation
================
Comprehensive evaluation metrics and reporting for health risk models.

Provides:
- Standard classification metrics (accuracy, AUC, precision, recall, F1)
- Calibration assessment (reliability diagrams, Brier score)
- Threshold analysis for risk stratification
- Visual reports for dissertation documentation
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config import DIABETES_CONFIG

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """
    Comprehensive model evaluation for health risk prediction.

    Computes multiple metrics important for clinical decision support:
    - Discrimination: How well the model separates cases from non-cases
    - Calibration: How well predicted probabilities match observed frequencies
    - Clinical utility: Performance at different risk thresholds

    Example:
        >>> evaluator = ModelEvaluator()
        >>> metrics = evaluator.evaluate(y_true, y_pred, y_proba)
        >>> report = evaluator.generate_report(y_true, y_pred, y_proba)
    """

    def __init__(self, target_accuracy: float = 0.80, target_auc: float = 0.80):
        """
        Initialize evaluator with target metrics.

        Args:
            target_accuracy: Target accuracy threshold (default: 80%)
            target_auc: Target AUC threshold (default: 0.80)
        """
        self.target_accuracy = target_accuracy
        self.target_auc = target_auc

    def compute_basic_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray, y_proba: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        Compute standard classification metrics.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_proba: Predicted probabilities for positive class

        Returns:
            Dictionary of metric names and values
        """
        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision_score(y_true, y_pred, zero_division=0),
            "recall": recall_score(y_true, y_pred, zero_division=0),
            "sensitivity": recall_score(y_true, y_pred, zero_division=0),  # Same as recall
            "f1_score": f1_score(y_true, y_pred, zero_division=0),
        }

        # Compute specificity
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        metrics["specificity"] = tn / (tn + fp) if (tn + fp) > 0 else 0
        metrics["true_positives"] = int(tp)
        metrics["true_negatives"] = int(tn)
        metrics["false_positives"] = int(fp)
        metrics["false_negatives"] = int(fn)

        # Probability-based metrics
        if y_proba is not None:
            metrics["roc_auc"] = roc_auc_score(y_true, y_proba)
            metrics["brier_score"] = brier_score_loss(y_true, y_proba)
            metrics["log_loss"] = log_loss(y_true, y_proba)

        return metrics

    def compute_threshold_metrics(
        self, y_true: np.ndarray, y_proba: np.ndarray, thresholds: Optional[List[float]] = None
    ) -> pd.DataFrame:
        """
        Compute metrics at different probability thresholds.

        Useful for selecting optimal threshold based on clinical requirements.

        Args:
            y_true: True labels
            y_proba: Predicted probabilities
            thresholds: List of thresholds to evaluate

        Returns:
            DataFrame with metrics at each threshold
        """
        if thresholds is None:
            thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

        results = []
        for threshold in thresholds:
            y_pred = (y_proba >= threshold).astype(int)
            metrics = self.compute_basic_metrics(y_true, y_pred, y_proba)
            metrics["threshold"] = threshold
            results.append(metrics)

        df = pd.DataFrame(results)
        df = df[["threshold", "accuracy", "precision", "recall", "specificity", "f1_score"]]

        return df

    def compute_calibration_metrics(
        self, y_true: np.ndarray, y_proba: np.ndarray, n_bins: int = 10
    ) -> Dict[str, Any]:
        """
        Assess model calibration.

        Good calibration means a predicted probability of 0.7 should correspond
        to approximately 70% of those cases actually being positive.

        Args:
            y_true: True labels
            y_proba: Predicted probabilities
            n_bins: Number of bins for calibration curve

        Returns:
            Dictionary with calibration metrics and curve data
        """
        # Calibration curve
        prob_true, prob_pred = calibration_curve(y_true, y_proba, n_bins=n_bins)

        # Expected Calibration Error (ECE) - simplified calculation
        # Use the actual number of bins returned by calibration_curve
        n_actual_bins = len(prob_true)
        bin_counts = np.histogram(y_proba, bins=n_actual_bins, range=(0, 1))[0]

        # Ensure same length for calculation
        if len(bin_counts) != len(prob_true):
            # Fall back to simple ECE calculation
            ece = np.mean(np.abs(prob_true - prob_pred))
        else:
            ece = np.sum(np.abs(prob_true - prob_pred) * bin_counts) / len(y_proba)

        return {
            "brier_score": brier_score_loss(y_true, y_proba),
            "expected_calibration_error": ece,
            "calibration_curve": {
                "mean_predicted_probability": prob_pred.tolist(),
                "fraction_of_positives": prob_true.tolist(),
            },
        }

    def compute_roc_curve(self, y_true: np.ndarray, y_proba: np.ndarray) -> Dict[str, Any]:
        """
        Compute ROC curve data.

        Args:
            y_true: True labels
            y_proba: Predicted probabilities

        Returns:
            Dictionary with FPR, TPR, thresholds, and AUC
        """
        fpr, tpr, thresholds = roc_curve(y_true, y_proba)
        auc = roc_auc_score(y_true, y_proba)

        # Find optimal threshold (Youden's J statistic)
        j_scores = tpr - fpr
        optimal_idx = np.argmax(j_scores)
        optimal_threshold = thresholds[optimal_idx]

        return {
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "thresholds": thresholds.tolist(),
            "auc": auc,
            "optimal_threshold": optimal_threshold,
            "optimal_tpr": tpr[optimal_idx],
            "optimal_fpr": fpr[optimal_idx],
        }

    def compute_precision_recall_curve(
        self, y_true: np.ndarray, y_proba: np.ndarray
    ) -> Dict[str, Any]:
        """
        Compute precision-recall curve data.

        Particularly useful for imbalanced datasets like diabetes prediction.

        Args:
            y_true: True labels
            y_proba: Predicted probabilities

        Returns:
            Dictionary with precision, recall, and thresholds
        """
        precision, recall, thresholds = precision_recall_curve(y_true, y_proba)

        # Average precision (area under PR curve)
        from sklearn.metrics import average_precision_score

        ap = average_precision_score(y_true, y_proba)

        return {
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "thresholds": thresholds.tolist(),
            "average_precision": ap,
        }

    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        Comprehensive model evaluation.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_proba: Predicted probabilities
            verbose: Whether to print results

        Returns:
            Dictionary with all metrics and analysis
        """
        results = {"basic_metrics": self.compute_basic_metrics(y_true, y_pred, y_proba)}

        if y_proba is not None:
            results["calibration"] = self.compute_calibration_metrics(y_true, y_proba)
            results["roc_curve"] = self.compute_roc_curve(y_true, y_proba)
            results["pr_curve"] = self.compute_precision_recall_curve(y_true, y_proba)
            results["threshold_analysis"] = self.compute_threshold_metrics(y_true, y_proba).to_dict(
                "records"
            )

        # Check against targets
        results["targets_met"] = {
            "accuracy": results["basic_metrics"]["accuracy"] >= self.target_accuracy,
            "auc": (
                results["basic_metrics"].get("roc_auc", 0) >= self.target_auc
                if y_proba is not None
                else None
            ),
        }

        if verbose:
            self._print_summary(results)

        return results

    def _print_summary(self, results: Dict[str, Any]) -> None:
        """Print evaluation summary."""
        metrics = results["basic_metrics"]

        print("\n" + "=" * 60)
        print("MODEL EVALUATION SUMMARY")
        print("=" * 60)

        print("\n📊 Classification Metrics:")
        print(
            f"  Accuracy:    {metrics['accuracy']:.4f} {'✓' if results['targets_met']['accuracy'] else '✗'} (target: {self.target_accuracy})"
        )

        if "roc_auc" in metrics:
            print(
                f"  ROC-AUC:     {metrics['roc_auc']:.4f} {'✓' if results['targets_met']['auc'] else '✗'} (target: {self.target_auc})"
            )

        print(f"  Precision:   {metrics['precision']:.4f}")
        print(f"  Recall:      {metrics['recall']:.4f}")
        print(f"  F1-Score:    {metrics['f1_score']:.4f}")
        print(f"  Specificity: {metrics['specificity']:.4f}")

        print("\n📋 Confusion Matrix:")
        print(f"  True Positives:  {metrics['true_positives']}")
        print(f"  True Negatives:  {metrics['true_negatives']}")
        print(f"  False Positives: {metrics['false_positives']}")
        print(f"  False Negatives: {metrics['false_negatives']}")

        if "calibration" in results:
            print("\n📈 Calibration:")
            print(f"  Brier Score: {results['calibration']['brier_score']:.4f}")
            print(f"  ECE:         {results['calibration']['expected_calibration_error']:.4f}")

        if "roc_curve" in results:
            print("\n🎯 Optimal Threshold (Youden's J):")
            print(f"  Threshold:   {results['roc_curve']['optimal_threshold']:.3f}")
            print(f"  Sensitivity: {results['roc_curve']['optimal_tpr']:.4f}")
            print(f"  Specificity: {1 - results['roc_curve']['optimal_fpr']:.4f}")

        print("\n" + "=" * 60)

    def generate_classification_report(self, y_true: np.ndarray, y_pred: np.ndarray) -> str:
        """
        Generate sklearn classification report.

        Args:
            y_true: True labels
            y_pred: Predicted labels

        Returns:
            Formatted classification report string
        """
        return classification_report(y_true, y_pred, target_names=["No Diabetes", "Diabetes"])


def main():
    """Demo of model evaluation."""
    print("\nModel Evaluator - Ready")
    print("Usage:")
    print("  evaluator = ModelEvaluator()")
    print("  results = evaluator.evaluate(y_true, y_pred, y_proba)")


if __name__ == "__main__":
    main()
