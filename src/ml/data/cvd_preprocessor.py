"""
CVD Data Preprocessor
=====================
Transforms raw NHANES data into features for cardiovascular disease (CVD) risk prediction.

Target Variable:
    Composite CVD outcome — positive if a doctor ever diagnosed any of:
    - Congestive heart failure (MCQ160B)
    - Coronary heart disease (MCQ160C)
    - Angina / angina pectoris (MCQ160D)
    - Heart attack / myocardial infarction (MCQ160E)
    - Stroke (MCQ160F)

Feature Set (mirrors Framingham Risk Score inputs + NHANES extras):
    - Demographic: age, gender, race/ethnicity, education, income
    - Anthropometric: BMI, waist circumference
    - Clinical: systolic/diastolic BP, total cholesterol, HDL, HbA1c, fasting glucose
    - Derived: diabetes indicator, BMI category, age group, hypertension flag
    - Lifestyle: smoking status, physical activity level

Required NHANES datasets:
    DEMO, BMX, BPX, GHB, GLU, TCHOL, HDL, DIQ, SMQ, PAQ, MCQ
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

from config import PROCESSED_DATA_DIR, CVD_CONFIG

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# NHANES Variable Mappings for CVD
# ─────────────────────────────────────────────

NHANES_VARIABLE_MAP = {
    # Demographics (DEMO)
    "age":            "RIDAGEYR",
    "gender":         "RIAGENDR",   # 1=Male, 2=Female
    "race_ethnicity": "RIDRETH3",
    "education":      "DMDEDUC2",
    "income_ratio":   "INDFMPIR",

    # Body Measures (BMX)
    "bmi":               "BMXBMI",
    "waist_circumference": "BMXWAIST",

    # Blood Pressure (BPX) — valid CVD risk inputs (Framingham)
    "systolic_bp":  "BPXSY1",
    "diastolic_bp": "BPXDI1",

    # Glycohemoglobin (GHB)
    "hba1c": "LBXGH",

    # Plasma Glucose (GLU)
    "fasting_glucose": "LBXGLU",

    # Cholesterol (TCHOL, HDL)
    "total_cholesterol": "LBXTC",
    "hdl_cholesterol":   "LBDHDD",

    # Diabetes Questionnaire (DIQ) — used to derive diabetes_indicator feature
    "doctor_diabetes": "DIQ010",
    "family_diabetes": "DIQ175A",

    # Smoking (SMQ)
    "smoked_100":     "SMQ020",
    "current_smoker": "SMQ040",

    # Physical Activity (PAQ)
    "vigorous_work":    "PAQ605",
    "moderate_work":    "PAQ620",
    "vigorous_rec":     "PAQ650",
    "moderate_rec":     "PAQ665",
    "sedentary_minutes": "PAD680",

    # Medical Conditions (MCQ) — TARGET variables
    "cvd_heart_failure": "MCQ160B",  # Congestive heart failure
    "cvd_chd":           "MCQ160C",  # Coronary heart disease
    "cvd_angina":        "MCQ160D",  # Angina
    "cvd_heart_attack":  "MCQ160E",  # Heart attack / MI
    "cvd_stroke":        "MCQ160F",  # Stroke
}

# MCQ target columns — excluded from feature set
CVD_TARGET_COLS = [
    "cvd_heart_failure", "cvd_chd", "cvd_angina",
    "cvd_heart_attack", "cvd_stroke",
]


class CVDPreprocessor:
    """
    Preprocesses NHANES data for cardiovascular disease (CVD) risk prediction.

    Creates a dataset suitable for training an XGBoost CVD risk classifier
    following the Framingham Risk Score feature paradigm.

    Example:
        >>> preprocessor = CVDPreprocessor()
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

        Args:
            df: Raw merged NHANES DataFrame

        Returns:
            DataFrame with renamed features
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
            f"Extracted {len(feature_df.columns)} features from {len(df.columns)} raw variables"
        )
        return feature_df

    # ──────────────────────────────────────────
    # Step 2: Create composite CVD target
    # ──────────────────────────────────────────

    def create_cvd_target(self, df: pd.DataFrame) -> pd.Series:
        """
        Create binary CVD target variable.

        CVD positive if a doctor ever diagnosed heart failure, coronary heart
        disease, angina, heart attack, or stroke (MCQ160B-F = 1).

        Args:
            df: Feature DataFrame

        Returns:
            Binary Series: 1 = CVD positive, 0 = CVD negative
        """
        cvd = pd.Series(False, index=df.index, name="cvd_status")

        for col in CVD_TARGET_COLS:
            if col in df.columns:
                cvd = cvd | (df[col] == 1)

        cvd = cvd.astype(int)

        n_cvd = cvd.sum()
        n_total = len(cvd)
        logger.info(
            f"CVD target: {n_cvd} positive ({100 * n_cvd / n_total:.1f}%) out of {n_total}"
        )
        return cvd

    # ──────────────────────────────────────────
    # Step 3: Derived features
    # ──────────────────────────────────────────

    def create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create clinically meaningful derived features.

        Derived features:
          - age_group: Binned age (18-35, 36-45, 46-55, 56-65, 65+)
          - bmi_category: WHO BMI classification
          - diabetes_indicator: HbA1c >= 6.5 or fasting glucose >= 126 or doctor diagnosed
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

        # Diabetes indicator (used as CVD risk feature)
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
        """
        Impute missing values using median (numeric) and mode (categorical).
        """
        df = df.copy()

        missing = df.isnull().sum()
        for col in df.columns:
            if missing[col] > 0:
                pct = 100 * missing[col] / len(df)
                logger.info(f"  Missing {col}: {missing[col]} ({pct:.1f}%)")

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
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
        - race_ethnicity: one-hot
        - smoking_status, activity_level, bmi_category, age_group: one-hot (drop_first=True)
        """
        df = df.copy()

        # Binary gender encoding
        if "gender" in df.columns:
            df["gender"] = df["gender"].map({1: 0, 2: 1})

        # One-hot encode nominal categoricals
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
        Run the complete CVD preprocessing pipeline.

        Args:
            raw_df: Raw merged NHANES DataFrame (must include MCQ columns)
            test_size: Proportion held out for testing
            random_state: Seed for reproducibility

        Returns:
            (X_train, X_test, y_train, y_test)

        Raises:
            ValueError: If no MCQ CVD variables found in the data
        """
        logger.info("=" * 50)
        logger.info("CVD Preprocessing Pipeline")
        logger.info("=" * 50)

        # Verify at least one MCQ target column exists
        mcq_nhanes_vars = [NHANES_VARIABLE_MAP[col] for col in CVD_TARGET_COLS]
        found_mcq = [v for v in mcq_nhanes_vars if v in raw_df.columns]
        if not found_mcq:
            raise ValueError(
                "No MCQ CVD variables found in data. "
                "Ensure MCQ dataset is downloaded and merged. "
                "Required: MCQ160B, MCQ160C, MCQ160D, MCQ160E, MCQ160F."
            )

        # Step 1: Extract
        logger.info("Step 1: Extracting features")
        df = self.extract_features(raw_df)

        # Step 2: Target
        logger.info("Step 2: Creating CVD target variable")
        y = self.create_cvd_target(df)

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

        # Step 7: Build final feature matrix — exclude target & raw CVD columns
        exclude_cols = (
            ["SEQN", "doctor_diabetes"]
            + CVD_TARGET_COLS
        )
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        X = df[feature_cols]

        self.feature_names = feature_cols
        logger.info(f"Final feature set: {len(feature_cols)} features")

        # Step 8: Stratified split
        logger.info("Step 8: Stratified train/test split")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        logger.info(f"Train: {len(X_train)} samples | Test: {len(X_test)} samples")
        logger.info(
            f"CVD prevalence — Train: {y_train.mean():.1%} | Test: {y_test.mean():.1%}"
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
        """Save processed CVD datasets to CSV files."""
        output_dir = output_dir or (PROCESSED_DATA_DIR / "cvd")
        output_dir.mkdir(parents=True, exist_ok=True)

        X_train.to_csv(output_dir / "X_train.csv", index=False)
        X_test.to_csv(output_dir / "X_test.csv", index=False)
        y_train.to_csv(output_dir / "y_train.csv", index=False)
        y_test.to_csv(output_dir / "y_test.csv", index=False)

        with open(output_dir / "feature_names.txt", "w") as f:
            f.write("\n".join(self.feature_names))

        logger.info(f"Processed CVD data saved to {output_dir}")


def main():
    print("\nCVD Preprocessor — Ready")
    print("Usage:")
    print("  preprocessor = CVDPreprocessor()")
    print("  X_train, X_test, y_train, y_test = preprocessor.prepare_data(raw_df)")
    print("  (raw_df must include MCQ dataset for CVD target variables)")


if __name__ == "__main__":
    main()
