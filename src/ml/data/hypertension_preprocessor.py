"""
Hypertension Data Preprocessor
================================
Transforms raw NHANES data into features for hypertension risk prediction.

Target Variable:
    Hypertension = systolic BP >= 140 mmHg OR diastolic BP >= 90 mmHg
    (derived from BPX blood pressure measurements already downloaded).
    First available reading pair is used (BPXOSY1 / BPXODI1).

Feature Set (blood pressure readings deliberately EXCLUDED to avoid circularity):
    - Demographic: age, gender, race/ethnicity, education, income
    - Anthropometric: BMI, waist circumference
    - Clinical: total cholesterol, HDL, HbA1c, fasting glucose
    - Derived: diabetes indicator, BMI category, age group
    - Lifestyle: smoking status, physical activity level, sedentary minutes

Note on design choice:
    Including BP readings as features would trivially "predict" hypertension because
    the target IS defined from those readings.  By excluding them we build a genuine
    preventive model: given demographic and lifestyle factors, who is at risk of
    developing hypertension?  A user without a recent BP measurement can still receive
    a risk estimate.

Required NHANES datasets:
    DEMO, BMX, BPX (target only), GHB, GLU, TCHOL, HDL, DIQ, SMQ, PAQ
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.impute import SimpleImputer

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config import PROCESSED_DATA_DIR, HYPERTENSION_CONFIG

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# NHANES Variable Mappings for Hypertension
# ─────────────────────────────────────────────

NHANES_VARIABLE_MAP = {
    # Demographics (DEMO)
    "age":            "RIDAGEYR",
    "gender":         "RIAGENDR",   # 1=Male, 2=Female
    "race_ethnicity": "RIDRETH3",
    "education":      "DMDEDUC2",
    "income_ratio":   "INDFMPIR",

    # Body Measures (BMX)
    "bmi":                "BMXBMI",
    "waist_circumference": "BMXWAIST",

    # Blood Pressure (BPX) — used for TARGET ONLY, not as features
    "systolic_bp":  "BPXSY1",
    "diastolic_bp": "BPXDI1",

    # Glycohemoglobin (GHB)
    "hba1c": "LBXGH",

    # Plasma Glucose (GLU)
    "fasting_glucose": "LBXGLU",

    # Cholesterol (TCHOL, HDL)
    "total_cholesterol": "LBXTC",
    "hdl_cholesterol":   "LBDHDD",

    # Diabetes Questionnaire (DIQ)
    "doctor_diabetes": "DIQ010",

    # Smoking (SMQ)
    "smoked_100":     "SMQ020",
    "current_smoker": "SMQ040",

    # Physical Activity (PAQ)
    "vigorous_work":     "PAQ605",
    "moderate_work":     "PAQ620",
    "vigorous_rec":      "PAQ650",
    "moderate_rec":      "PAQ665",
    "sedentary_minutes": "PAD680",
}

# Columns used to define the target — excluded from the feature set
BP_TARGET_COLS = ["systolic_bp", "diastolic_bp"]


class HypertensionPreprocessor:
    """
    Preprocesses NHANES data for hypertension risk prediction.

    Blood pressure readings (systolic_bp / diastolic_bp) are included as
    **optional** features.  They are never imputed — XGBoost learns the
    optimal split direction for missing values, so the model works in two
    modes:
      • BP provided  → uses it as a strong signal alongside lifestyle factors
      • BP unknown   → falls back to demographics/lifestyle only

    The target is measured hypertension (BP >= 140/90) from the SAME NHANES
    reading, so rows where BP is NaN are excluded from training (no target),
    but partial-match rows (one reading NaN) are handled by taking the other.

    Example:
        >>> preprocessor = HypertensionPreprocessor()
        >>> X_train, X_test, y_train, y_test = preprocessor.prepare_data(raw_df)
    """

    def __init__(self):
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.imputers: Dict[str, SimpleImputer] = {}
        self.feature_names: List[str] = []
        self.is_fitted = False

    # ──────────────────────────────────────────
    # Step 1: Extract features from raw NHANES
    # ──────────────────────────────────────────

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract and rename features from raw NHANES merged DataFrame.

        Includes BP columns so the target can be computed, but they will be
        removed from the feature matrix in a later step.
        """
        features = {}
        for feature_name, nhanes_var in NHANES_VARIABLE_MAP.items():
            if nhanes_var in df.columns:
                features[feature_name] = df[nhanes_var]
            else:
                logger.warning(f"Variable {nhanes_var} ({feature_name}) not found in data")

        feature_df = pd.DataFrame(features)

        if "SEQN" in df.columns:
            feature_df["SEQN"] = df["SEQN"]

        logger.info(
            f"Extracted {len(feature_df.columns)} columns from {len(df.columns)} raw variables"
        )
        return feature_df

    # ──────────────────────────────────────────
    # Step 2: Create hypertension target
    # ──────────────────────────────────────────

    def create_hypertension_target(self, df: pd.DataFrame) -> pd.Series:
        """
        Create binary hypertension target variable.

        Hypertension is defined as:
            systolic BP >= 140 mmHg OR diastolic BP >= 90 mmHg

        Args:
            df: Feature DataFrame (must contain systolic_bp and diastolic_bp)

        Returns:
            Binary Series: 1 = Hypertension, 0 = Normotensive

        Raises:
            ValueError: If blood pressure columns are missing
        """
        if "systolic_bp" not in df.columns or "diastolic_bp" not in df.columns:
            raise ValueError(
                "Blood pressure columns missing. Ensure BPX dataset is loaded. "
                "Required NHANES variables: BPXOSY1, BPXODI1."
            )

        hypertension = (
            (df["systolic_bp"] >= 140) | (df["diastolic_bp"] >= 90)
        ).astype(int)

        # Set NaN where BP readings themselves are NaN
        bp_missing = df["systolic_bp"].isna() | df["diastolic_bp"].isna()
        hypertension = hypertension.where(~bp_missing, other=np.nan)

        n_htn = int(hypertension.sum())
        n_total = hypertension.notna().sum()
        logger.info(
            f"Hypertension target: {n_htn} positive ({100 * n_htn / n_total:.1f}%) "
            f"out of {n_total} valid observations"
        )
        return hypertension.rename("hypertension_status")

    # ──────────────────────────────────────────
    # Step 3: Derived features
    # ──────────────────────────────────────────

    def create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create clinically meaningful derived features.

        Derived features:
          - age_group: Binned age (18-35, 36-45, 46-55, 56-65, 65+)
          - bmi_category: WHO BMI classification
          - diabetes_indicator: derived from HbA1c / glucose / doctor diagnosis
          - smoking_status: Never / Former / Current
          - activity_level: Sedentary / Low / Moderate / High
        """
        df = df.copy()

        # Age groups
        if "age" in df.columns:
            df["age_group"] = pd.cut(
                df["age"],
                bins=[0, 35, 45, 55, 65, 100],
                labels=["18-35", "36-45", "46-55", "56-65", "65+"],
            )

        # BMI categories (WHO)
        if "bmi" in df.columns:
            df["bmi_category"] = pd.cut(
                df["bmi"],
                bins=[0, 18.5, 25, 30, 35, 40, 100],
                labels=["Underweight", "Normal", "Overweight", "Obese_I", "Obese_II", "Obese_III"],
            )

        # Diabetes indicator (a known hypertension risk factor)
        diabetes = pd.Series(False, index=df.index)
        if "doctor_diabetes" in df.columns:
            diabetes = diabetes | (df["doctor_diabetes"] == 1)
        if "hba1c" in df.columns:
            diabetes = diabetes | (df["hba1c"] >= 6.5)
        if "fasting_glucose" in df.columns:
            diabetes = diabetes | (df["fasting_glucose"] >= 126)
        df["diabetes_indicator"] = diabetes.astype(int)

        # Smoking status
        if "smoked_100" in df.columns and "current_smoker" in df.columns:
            df["smoking_status"] = "Never"
            df.loc[df["smoked_100"] == 1, "smoking_status"] = "Former"
            df.loc[
                (df["smoked_100"] == 1) & (df["current_smoker"].isin([1, 2])),
                "smoking_status",
            ] = "Current"

        # Physical activity level
        activity_cols = ["vigorous_work", "moderate_work", "vigorous_rec", "moderate_rec"]
        if all(c in df.columns for c in activity_cols):
            activity_score = (
                (df["vigorous_work"] == 1).astype(int) * 2
                + (df["moderate_work"] == 1).astype(int)
                + (df["vigorous_rec"] == 1).astype(int) * 2
                + (df["moderate_rec"] == 1).astype(int)
            )
            df["activity_level"] = pd.cut(
                activity_score,
                bins=[-1, 0, 2, 4, 10],
                labels=["Sedentary", "Low", "Moderate", "High"],
            )

        return df

    # ──────────────────────────────────────────
    # Step 4: Missing value imputation
    # ──────────────────────────────────────────

    def handle_missing_values(
        self, df: pd.DataFrame, strategy: str = "median"
    ) -> pd.DataFrame:
        """Impute missing values using median (numeric) and mode (categorical).

        BP columns (systolic_bp / diastolic_bp) are intentionally NOT imputed
        — they are left as NaN so XGBoost learns the optimal split direction
        for the "BP unknown" case during training.
        """
        df = df.copy()

        # Columns whose NaN carries meaning — do not impute
        no_impute = set(BP_TARGET_COLS)

        missing = df.isnull().sum()
        for col in df.columns:
            if missing[col] > 0:
                pct = 100 * missing[col] / len(df)
                logger.info(f"  Missing {col}: {missing[col]} ({pct:.1f}%)")

        numeric_cols = [
            c for c in df.select_dtypes(include=[np.number]).columns
            if c not in no_impute
        ]
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        if numeric_cols:
            imputer = SimpleImputer(strategy=strategy)
            df[numeric_cols] = imputer.fit_transform(df[numeric_cols])
            self.imputers["numeric"] = imputer

        if categorical_cols:
            cat_imputer = SimpleImputer(strategy="most_frequent")
            df[categorical_cols] = cat_imputer.fit_transform(df[categorical_cols])
            self.imputers["categorical"] = cat_imputer

        return df

    # ──────────────────────────────────────────
    # Step 5: Categorical encoding
    # ──────────────────────────────────────────

    def encode_categorical(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Encode categorical variables as numeric.

        - gender: binary (0=Male, 1=Female)
        - race_ethnicity, smoking_status, activity_level, bmi_category, age_group: one-hot
        """
        df = df.copy()

        if "gender" in df.columns:
            df["gender"] = df["gender"].map({1: 0, 2: 1})

        nominal_cols = [
            "race_ethnicity", "smoking_status", "activity_level",
            "bmi_category", "age_group",
        ]
        existing_nominal = [c for c in nominal_cols if c in df.columns]
        if existing_nominal:
            df = pd.get_dummies(df, columns=existing_nominal, drop_first=True)

        return df

    # ──────────────────────────────────────────
    # Full Pipeline
    # ──────────────────────────────────────────

    def prepare_data(
        self,
        raw_df: pd.DataFrame,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Run the complete hypertension preprocessing pipeline.

        Args:
            raw_df: Raw merged NHANES DataFrame (must include BPX columns)
            test_size: Proportion held out for testing
            random_state: Seed for reproducibility

        Returns:
            (X_train, X_test, y_train, y_test)
        """
        logger.info("=" * 50)
        logger.info("Hypertension Preprocessing Pipeline")
        logger.info("=" * 50)

        # Step 1: Extract
        logger.info("Step 1: Extracting features")
        df = self.extract_features(raw_df)

        # Step 2: Target (computed before removing BP columns)
        logger.info("Step 2: Creating hypertension target variable")
        y = self.create_hypertension_target(df)

        # Step 3: Derived features
        logger.info("Step 3: Creating derived features")
        df = self.create_derived_features(df)

        # Step 4: Filter valid samples (adults >= 18, valid target)
        logger.info("Step 4: Filtering valid samples")
        valid_mask = (df["age"] >= 18) & y.notna()
        df = df[valid_mask]
        y = y[valid_mask]
        logger.info(f"Valid samples after filtering: {len(df)}")

        # Step 5: Imputation
        logger.info("Step 5: Handling missing values")
        df = self.handle_missing_values(df)

        # Step 6: Encoding
        logger.info("Step 6: Encoding categorical variables")
        df = self.encode_categorical(df)

        # Step 7: Build final feature matrix
        # Exclude: SEQN, doctor_diabetes, and BP columns.
        # BP is NOT a model feature — it defines the target, so including it
        # creates perfect circularity.  When a user knows their BP, the service
        # layer applies AHA 2017 clinical thresholds directly on top of the
        # model's lifestyle-based score.
        exclude_cols = ["SEQN", "doctor_diabetes"] + BP_TARGET_COLS
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        X = df[feature_cols]

        self.feature_names = feature_cols
        logger.info(f"Final feature set: {len(feature_cols)} features")
        logger.info("BP excluded from features (clinical override applied at inference)")

        # Step 8: Stratified split
        logger.info("Step 8: Stratified train/test split")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y.astype(int), test_size=test_size, random_state=random_state, stratify=y
        )

        logger.info(f"Train: {len(X_train)} samples | Test: {len(X_test)} samples")
        logger.info(
            f"Hypertension prevalence — Train: {y_train.mean():.1%} | Test: {y_test.mean():.1%}"
        )

        self.is_fitted = True
        return X_train, X_test, y_train, y_test

    def save_processed_data(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
        output_dir: Optional[Path] = None,
    ) -> None:
        """Save processed hypertension datasets to CSV files."""
        output_dir = output_dir or (PROCESSED_DATA_DIR / "hypertension")
        output_dir.mkdir(parents=True, exist_ok=True)

        X_train.to_csv(output_dir / "X_train.csv", index=False)
        X_test.to_csv(output_dir / "X_test.csv", index=False)
        y_train.to_csv(output_dir / "y_train.csv", index=False)
        y_test.to_csv(output_dir / "y_test.csv", index=False)

        with open(output_dir / "feature_names.txt", "w") as f:
            f.write("\n".join(self.feature_names))

        logger.info(f"Processed hypertension data saved to {output_dir}")


def main():
    print("\nHypertension Preprocessor — Ready")
    print("Usage:")
    print("  preprocessor = HypertensionPreprocessor()")
    print("  X_train, X_test, y_train, y_test = preprocessor.prepare_data(raw_df)")
    print("  (raw_df must include BPX dataset for hypertension target)")


if __name__ == "__main__":
    main()
