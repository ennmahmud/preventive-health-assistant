#!/usr/bin/env python3
"""
Train Diabetes Risk Model
=========================
Complete training pipeline for the diabetes risk prediction model.

This script:
1. Loads and preprocesses NHANES data
2. Trains an XGBoost model with cross-validation
3. Evaluates performance against targets (≥80% accuracy)
4. Generates SHAP explanations
5. Saves the trained model

Usage:
    python src/ml/training/train_diabetes.py
    python src/ml/training/train_diabetes.py --cycles 2017-2018 2015-2016
    python src/ml/training/train_diabetes.py --skip-download
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

from config import DIABETES_CONFIG, MODELS_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.ml.data import DiabetesPreprocessor, NHANESDownloader, NHANESLoader
from src.ml.evaluation.metrics import ModelEvaluator
from src.ml.explainability.shap_explainer import SHAPExplainer
from src.ml.models.diabetes_model import DiabetesRiskModel

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def download_data(cycles: list[str], force: bool = False) -> bool:
    """
    Download NHANES datasets.

    Args:
        cycles: Survey cycles to download
        force: Force re-download

    Returns:
        True if successful
    """
    print("\n" + "=" * 60)
    print("STEP 1: DATA ACQUISITION")
    print("=" * 60)

    downloader = NHANESDownloader()

    # Essential datasets for diabetes model
    datasets = [
        "demographics",
        "body_measures",
        "blood_pressure",
        "glycohemoglobin",
        "plasma_glucose",
        "cholesterol_total",
        "cholesterol_hdl",
        "diabetes_questionnaire",
        "smoking",
        "physical_activity",
    ]

    results = downloader.download_all_cycles(cycles, datasets, force=True)

    # Check success
    total = sum(len(d) for d in results.values())
    successful = sum(1 for cycle in results.values() for path in cycle.values() if path)

    logger.info(f"Downloaded {successful}/{total} datasets")

    return successful > 0


def load_and_preprocess_data(cycles: list[str]) -> tuple:
    """
    Load and preprocess NHANES data.

    Args:
        cycles: Survey cycles to load

    Returns:
        Tuple of (X_train, X_test, y_train, y_test)
    """
    print("\n" + "=" * 60)
    print("STEP 2: DATA LOADING & PREPROCESSING")
    print("=" * 60)

    loader = NHANESLoader()

    # Dataset codes for merging
    dataset_codes = ["DEMO", "BMX", "BPX", "GHB", "GLU", "TCHOL", "HDL", "DIQ", "SMQ", "PAQ"]

    # Load and merge data from all cycles
    all_data = []
    for cycle in cycles:
        logger.info(f"Loading cycle: {cycle}")
        df = loader.load_and_merge(cycle, dataset_codes)
        if df is not None:
            df["survey_cycle"] = cycle
            all_data.append(df)
            logger.info(f"  Loaded {len(df)} records")

    if not all_data:
        raise ValueError("No data loaded from any cycle")

    # Combine all cycles
    raw_df = pd.concat(all_data, ignore_index=True)
    logger.info(f"Combined data: {len(raw_df)} total records")

    # Preprocess
    preprocessor = DiabetesPreprocessor()
    X_train, X_test, y_train, y_test = preprocessor.prepare_data(raw_df)

    # Save processed data
    preprocessor.save_processed_data(X_train, X_test, y_train, y_test)

    return X_train, X_test, y_train, y_test, preprocessor


def train_model(
    X_train: pd.DataFrame, X_test: pd.DataFrame, y_train: pd.Series, y_test: pd.Series
) -> DiabetesRiskModel:
    """
    Train the diabetes risk model.

    Args:
        X_train, X_test, y_train, y_test: Training and test data

    Returns:
        Trained model
    """
    print("\n" + "=" * 60)
    print("STEP 3: MODEL TRAINING")
    print("=" * 60)

    # Get model parameters from config
    params = DIABETES_CONFIG["model_params"]

    model = DiabetesRiskModel(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        learning_rate=params["learning_rate"],
        subsample=params["subsample"],
        colsample_bytree=params["colsample_bytree"],
        random_state=params["random_state"],
        early_stopping_rounds=params["early_stopping_rounds"],
    )

    # Cross-validation first
    logger.info("Running cross-validation...")
    cv_results = model.cross_validate(X_train, y_train, cv=5)

    print("\nCross-validation results:")
    for metric, scores in cv_results.items():
        print(f"  {metric}: {scores.mean():.4f} (+/- {scores.std()*2:.4f})")

    # Train final model with early stopping
    logger.info("\nTraining final model...")
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=True)

    return model


def evaluate_model(model: DiabetesRiskModel, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    """
    Evaluate the trained model.

    Args:
        model: Trained model
        X_test: Test features
        y_test: Test labels

    Returns:
        Evaluation results dictionary
    """
    print("\n" + "=" * 60)
    print("STEP 4: MODEL EVALUATION")
    print("=" * 60)

    # Get predictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    # Evaluate
    evaluator = ModelEvaluator(
        target_accuracy=DIABETES_CONFIG["validation"]["target_accuracy"],
        target_auc=DIABETES_CONFIG["validation"]["target_auc"],
    )

    results = evaluator.evaluate(y_test, y_pred, y_proba, verbose=True)

    # Print classification report
    print("\nClassification Report:")
    print(evaluator.generate_classification_report(y_test, y_pred))

    # Feature importance
    print("\nTop 10 Most Important Features:")
    importance_df = model.get_feature_importance()
    print(importance_df.head(10).to_string(index=False))

    return results


def generate_explanations(
    model: DiabetesRiskModel, X_train: pd.DataFrame, X_test: pd.DataFrame
) -> dict:
    """
    Generate SHAP explanations.

    Args:
        model: Trained model
        X_train: Training data (for background)
        X_test: Test data (for sample explanations)

    Returns:
        SHAP analysis results
    """
    print("\n" + "=" * 60)
    print("STEP 5: EXPLAINABILITY ANALYSIS")
    print("=" * 60)

    # Initialize SHAP explainer
    explainer = SHAPExplainer(
        model.model, feature_names=model.feature_names  # The underlying XGBoost model
    )

    # Use sample of training data as background
    background = X_train.sample(n=min(500, len(X_train)), random_state=42)
    explainer.initialize(background)

    # Global importance
    logger.info("Computing global feature importance...")
    global_importance = explainer.get_global_importance(X_test.head(500))

    print("\nSHAP Global Feature Importance (Top 10):")
    print(global_importance.head(10).to_string(index=False))

    # Sample individual explanation
    print("\nSample Individual Explanation:")
    sample_idx = X_test.head(1)
    explanation = explainer.explain_prediction(sample_idx)
    text_explanation = explainer.generate_text_explanation(explanation)
    print(text_explanation)

    return {
        "global_importance": global_importance.to_dict("records"),
        "sample_explanation": explanation,
    }


def save_results(model: DiabetesRiskModel, evaluation_results: dict, shap_results: dict) -> Path:
    """
    Save model and results.

    Args:
        model: Trained model
        evaluation_results: Evaluation metrics
        shap_results: SHAP analysis results

    Returns:
        Path to saved model
    """
    print("\n" + "=" * 60)
    print("STEP 6: SAVING RESULTS")
    print("=" * 60)

    # Save model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = model.save(version=timestamp)

    # Save evaluation results
    eval_path = MODELS_DIR / f"diabetes_evaluation_{timestamp}.json"

    # Convert numpy types for JSON serialization
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

    logger.info(f"Model saved: {model_path}")
    logger.info(f"Evaluation saved: {eval_path}")

    return model_path


def main():
    """Main training pipeline."""
    parser = argparse.ArgumentParser(description="Train diabetes risk prediction model")
    parser.add_argument(
        "--cycles",
        nargs="+",
        default=["2017-2018", "2015-2016"],
        help="NHANES survey cycles to use",
    )
    parser.add_argument(
        "--skip-download", action="store_true", help="Skip data download (use existing data)"
    )
    parser.add_argument("--force-download", action="store_true", help="Force re-download of data")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("DIABETES RISK MODEL TRAINING PIPELINE")
    print("=" * 60)
    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Survey cycles: {', '.join(args.cycles)}")
    print(f"Target accuracy: {DIABETES_CONFIG['validation']['target_accuracy']:.0%}")
    print(f"Target AUC: {DIABETES_CONFIG['validation']['target_auc']:.2f}")

    try:
        # Step 1: Download data
        if not args.skip_download:
            download_data(args.cycles, args.force_download)
        else:
            logger.info("Skipping data download")

        # Step 2: Load and preprocess
        X_train, X_test, y_train, y_test, preprocessor = load_and_preprocess_data(args.cycles)

        # Step 3: Train model
        model = train_model(X_train, X_test, y_train, y_test)

        # Step 4: Evaluate
        evaluation_results = evaluate_model(model, X_test, y_test)

        # Step 5: Generate explanations
        shap_results = generate_explanations(model, X_train, X_test)

        # Step 6: Save everything
        model_path = save_results(model, evaluation_results, shap_results)

        # Final summary
        print("\n" + "=" * 60)
        print("TRAINING COMPLETE")
        print("=" * 60)

        metrics = evaluation_results["basic_metrics"]
        targets_met = evaluation_results["targets_met"]

        print(f"\nFinal Results:")
        print(
            f"  Accuracy: {metrics['accuracy']:.4f} {'✓ PASSED' if targets_met['accuracy'] else '✗ BELOW TARGET'}"
        )
        print(
            f"  ROC-AUC:  {metrics['roc_auc']:.4f} {'✓ PASSED' if targets_met['auc'] else '✗ BELOW TARGET'}"
        )
        print(f"\nModel saved to: {model_path}")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Return status
        if targets_met["accuracy"] and targets_met["auc"]:
            print("\n🎉 All targets met! Model is ready for integration.")
            return 0
        else:
            print("\n⚠️  Some targets not met. Consider tuning hyperparameters.")
            return 1

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
