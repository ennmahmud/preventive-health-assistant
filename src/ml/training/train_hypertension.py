#!/usr/bin/env python3
"""
Train Hypertension Risk Model
==============================
Complete training pipeline for the hypertension risk prediction model.

This script:
1. Loads NHANES data (BPX already downloaded — provides target variable)
2. Loads and merges datasets from multiple survey cycles
3. Preprocesses features using HypertensionPreprocessor
   — blood pressure readings are EXCLUDED from features
4. Trains an XGBoost model with cross-validation
5. Evaluates performance
6. Generates SHAP explanations
7. Saves the trained model

Usage:
    python src/ml/training/train_hypertension.py
    python src/ml/training/train_hypertension.py --skip-download
    python src/ml/training/train_hypertension.py --cycles 2017-2018 2015-2016
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import numpy as np
import pandas as pd

from config import HYPERTENSION_CONFIG, MODELS_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.ml.data import NHANESDownloader, NHANESLoader
from src.ml.data.hypertension_preprocessor import HypertensionPreprocessor
from src.ml.evaluation.metrics import ModelEvaluator
from src.ml.explainability.shap_explainer import SHAPExplainer
from src.ml.models.hypertension_model import HypertensionRiskModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Pipeline Steps
# ─────────────────────────────────────────────

def download_data(cycles: list, force: bool = False) -> bool:
    """
    Download NHANES datasets required for hypertension model.

    BPX (blood pressure) is already downloaded from the diabetes pipeline
    and provides the target variable.  No extra datasets required.
    """
    print("\n" + "=" * 60)
    print("STEP 1: DATA ACQUISITION")
    print("=" * 60)

    downloader = NHANESDownloader()

    # All datasets needed (BPX included for target)
    datasets = [
        "demographics",
        "body_measures",
        "blood_pressure",   # BPX — used for target variable
        "glycohemoglobin",
        "plasma_glucose",
        "cholesterol_total",
        "cholesterol_hdl",
        "diabetes_questionnaire",
        "smoking",
        "physical_activity",
    ]

    results = downloader.download_all_cycles(cycles, datasets, force=force)

    total = sum(len(d) for d in results.values())
    successful = sum(1 for cycle in results.values() for path in cycle.values() if path)
    logger.info(f"Downloaded {successful}/{total} datasets")
    return successful > 0


def load_and_preprocess_data(cycles: list) -> tuple:
    """
    Load and preprocess NHANES data for hypertension prediction.

    Args:
        cycles: Survey cycles to load

    Returns:
        (X_train, X_test, y_train, y_test, preprocessor)
    """
    print("\n" + "=" * 60)
    print("STEP 2: DATA LOADING & PREPROCESSING")
    print("=" * 60)

    loader = NHANESLoader()

    # Dataset codes — BPX provides the target
    dataset_codes = [
        "DEMO", "BMX", "BPX", "GHB", "GLU", "TCHOL", "HDL",
        "DIQ", "SMQ", "PAQ",
    ]

    all_data = []
    for cycle in cycles:
        logger.info(f"Loading cycle: {cycle}")
        df = loader.load_and_merge(cycle, dataset_codes)
        if df is not None:
            df["survey_cycle"] = cycle
            all_data.append(df)
            logger.info(f"  Loaded {len(df)} records from {cycle}")

    if not all_data:
        raise ValueError("No data loaded from any cycle. Run with --force-download.")

    raw_df = pd.concat(all_data, ignore_index=True)
    logger.info(f"Combined data: {len(raw_df)} total records")

    preprocessor = HypertensionPreprocessor()
    X_train, X_test, y_train, y_test = preprocessor.prepare_data(raw_df)
    preprocessor.save_processed_data(X_train, X_test, y_train, y_test)

    return X_train, X_test, y_train, y_test, preprocessor


def train_model(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> HypertensionRiskModel:
    """Train the hypertension risk model with cross-validation."""
    print("\n" + "=" * 60)
    print("STEP 3: MODEL TRAINING")
    print("=" * 60)

    params = HYPERTENSION_CONFIG["model_params"]

    model = HypertensionRiskModel(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        learning_rate=params["learning_rate"],
        subsample=params["subsample"],
        colsample_bytree=params["colsample_bytree"],
        random_state=params["random_state"],
        early_stopping_rounds=params["early_stopping_rounds"],
    )

    logger.info("Running 5-fold cross-validation...")
    cv_results = model.cross_validate(X_train, y_train, cv=5)

    print("\nCross-validation results:")
    for metric, scores in cv_results.items():
        print(f"  {metric}: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")

    logger.info("\nTraining final model with early stopping...")
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=True)

    return model


def evaluate_model(
    model: HypertensionRiskModel, X_test: pd.DataFrame, y_test: pd.Series
) -> dict:
    """Evaluate the trained hypertension model."""
    print("\n" + "=" * 60)
    print("STEP 4: MODEL EVALUATION")
    print("=" * 60)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    evaluator = ModelEvaluator(
        target_accuracy=HYPERTENSION_CONFIG["validation"]["target_accuracy"],
        target_auc=HYPERTENSION_CONFIG["validation"]["target_auc"],
    )

    results = evaluator.evaluate(y_test, y_pred, y_proba, verbose=True)

    print("\nClassification Report:")
    from sklearn.metrics import classification_report
    print(
        classification_report(
            y_test, y_pred,
            target_names=["Normotensive", "Hypertensive"],
        )
    )

    print("\nTop 10 Most Important Features:")
    importance_df = model.get_feature_importance()
    print(importance_df.head(10).to_string(index=False))

    return results


def generate_explanations(
    model: HypertensionRiskModel, X_train: pd.DataFrame, X_test: pd.DataFrame
) -> dict:
    """Generate SHAP feature explanations."""
    print("\n" + "=" * 60)
    print("STEP 5: EXPLAINABILITY ANALYSIS")
    print("=" * 60)

    explainer = SHAPExplainer(model.model, feature_names=model.feature_names)

    background = X_train.sample(n=min(500, len(X_train)), random_state=42)
    explainer.initialize(background)

    logger.info("Computing global feature importance via SHAP...")
    global_importance = explainer.get_global_importance(X_test.head(500))

    print("\nSHAP Global Feature Importance (Top 10):")
    print(global_importance.head(10).to_string(index=False))

    sample_explanation = explainer.explain_prediction(X_test.head(1))
    text_explanation = explainer.generate_text_explanation(sample_explanation)
    print("\nSample Individual Explanation:")
    print(text_explanation)

    return {
        "global_importance": global_importance.to_dict("records"),
        "sample_explanation": sample_explanation,
    }


def save_results(
    model: HypertensionRiskModel, evaluation_results: dict, shap_results: dict
) -> Path:
    """Save model and evaluation results."""
    print("\n" + "=" * 60)
    print("STEP 6: SAVING RESULTS")
    print("=" * 60)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = model.save(version=timestamp)

    eval_path = MODELS_DIR / f"hypertension_evaluation_{timestamp}.json"

    def convert_numpy(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(i) for i in obj]
        return obj

    results_to_save = {
        "evaluation": convert_numpy(evaluation_results),
        "shap_global_importance": shap_results["global_importance"],
        "timestamp": timestamp,
    }

    with open(eval_path, "w") as f:
        json.dump(results_to_save, f, indent=2, default=str)

    logger.info(f"Hypertension model saved: {model_path}")
    logger.info(f"Evaluation saved:         {eval_path}")
    return model_path


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Train hypertension risk prediction model")
    parser.add_argument(
        "--cycles",
        nargs="+",
        default=["2017-2018", "2015-2016"],
        help="NHANES survey cycles to use",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip data download (use existing files)",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Force re-download of all datasets",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("HYPERTENSION RISK MODEL TRAINING PIPELINE")
    print("=" * 60)
    print(f"\nStart time:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Survey cycles:   {', '.join(args.cycles)}")
    print(f"Target accuracy: {HYPERTENSION_CONFIG['validation']['target_accuracy']:.0%}")
    print(f"Target AUC:      {HYPERTENSION_CONFIG['validation']['target_auc']:.2f}")
    print(f"\nNote: BP readings are excluded from features (preventive model).")

    try:
        if not args.skip_download:
            download_data(args.cycles, args.force_download)
        else:
            logger.info("Skipping data download (--skip-download)")

        X_train, X_test, y_train, y_test, preprocessor = load_and_preprocess_data(args.cycles)
        model = train_model(X_train, X_test, y_train, y_test)
        evaluation_results = evaluate_model(model, X_test, y_test)
        shap_results = generate_explanations(model, X_train, X_test)
        model_path = save_results(model, evaluation_results, shap_results)

        print("\n" + "=" * 60)
        print("TRAINING COMPLETE")
        print("=" * 60)

        metrics = evaluation_results["basic_metrics"]
        targets_met = evaluation_results["targets_met"]

        print(f"\nFinal Results:")
        print(
            f"  Accuracy: {metrics['accuracy']:.4f} "
            f"{'✓ PASSED' if targets_met['accuracy'] else '✗ BELOW TARGET'}"
        )
        print(
            f"  ROC-AUC:  {metrics['roc_auc']:.4f} "
            f"{'✓ PASSED' if targets_met['auc'] else '✗ BELOW TARGET'}"
        )
        print(f"\nModel saved to: {model_path}")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if targets_met["accuracy"] and targets_met["auc"]:
            print("\n🎉 All targets met! Hypertension model ready for integration.")
            return 0
        else:
            print("\n⚠️  Some targets not met. Consider tuning hyperparameters.")
            return 1

    except Exception as e:
        logger.error(f"Hypertension training failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
