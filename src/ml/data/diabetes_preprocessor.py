"""
Diabetes Data Preprocessor
==========================
Transforms raw NHANES data into features for diabetes risk prediction.

This module handles:
- Feature extraction from raw NHANES variables
- Missing value imputation
- Feature encoding (categorical → numeric)
- Target variable creation (diabetes status)
- Train/test splitting with stratification
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config import PROCESSED_DATA_DIR, DIABETES_CONFIG

logger = logging.getLogger(__name__)


# NHANES Variable Mappings
# Maps our feature names to actual NHANES variable codes

NHANES_VARIABLE_MAP = {
    # Demographics (DEMO)
    "age": "RIDAGEYR",           # Age in years at screening
    "gender": "RIAGENDR",        # Gender (1=Male, 2=Female)
    "race_ethnicity": "RIDRETH3", # Race/Hispanic origin with NH Asian
    "education": "DMDEDUC2",     # Education level (adults 20+)
    "income_ratio": "INDFMPIR",  # Family income to poverty ratio
    
    # Body Measures (BMX)
    "bmi": "BMXBMI",             # Body Mass Index (kg/m²)
    "waist_circumference": "BMXWAIST",  # Waist circumference (cm)
    "weight": "BMXWT",           # Weight (kg)
    "height": "BMXHT",           # Standing height (cm)
    
    # Blood Pressure (BPX)
    "systolic_bp": "BPXOSY1",    # Systolic BP - 1st oscillometric reading
    "diastolic_bp": "BPXODI1",   # Diastolic BP - 1st oscillometric reading
    
    # Glycohemoglobin (GHB)
    "hba1c": "LBXGH",            # Glycohemoglobin (%)
    
    # Plasma Glucose (GLU)
    "fasting_glucose": "LBXGLU", # Fasting glucose (mg/dL)
    "fasting_insulin": "LBXIN",  # Fasting insulin (µU/mL)
    
    # Cholesterol (TCHOL, HDL)
    "total_cholesterol": "LBXTC",  # Total cholesterol (mg/dL)
    "hdl_cholesterol": "LBDHDD",   # Direct HDL-Cholesterol (mg/dL)
    
    # Diabetes Questionnaire (DIQ)
    "doctor_diabetes": "DIQ010",    # Doctor told you have diabetes
    "prediabetes": "DIQ160",        # Ever told you have prediabetes
    "family_diabetes": "DIQ175A",   # Family history - biological relatives
    "age_diabetes_diagnosis": "DID040",  # Age when first told
    
    # Smoking (SMQ)
    "smoked_100": "SMQ020",      # Smoked at least 100 cigarettes
    "current_smoker": "SMQ040",  # Do you now smoke cigarettes
    
    # Physical Activity (PAQ)
    "vigorous_work": "PAQ605",   # Vigorous work activity
    "moderate_work": "PAQ620",   # Moderate work activity
    "vigorous_rec": "PAQ650",    # Vigorous recreational activities
    "moderate_rec": "PAQ665",    # Moderate recreational activities
    "sedentary_minutes": "PAD680", # Minutes of sedentary activity
}


class DiabetesPreprocessor:
    """
    Preprocesses NHANES data for diabetes risk prediction.
    
    This class creates a standardized dataset with:
    - Clinically relevant features
    - Properly encoded categorical variables
    - Imputed missing values
    - Binary target variable for diabetes status
    
    Example:
        >>> preprocessor = DiabetesPreprocessor()
        >>> X_train, X_test, y_train, y_test = preprocessor.prepare_data(raw_df)
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.imputers: Dict[str, SimpleImputer] = {}
        self.feature_names: List[str] = []
        self.is_fitted = False
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract and rename features from raw NHANES data.
        
        Args:
            df: Raw NHANES merged DataFrame
            
        Returns:
            DataFrame with extracted features
        """
        features = {}
        
        # Extract each feature if available
        for feature_name, nhanes_var in NHANES_VARIABLE_MAP.items():
            if nhanes_var in df.columns:
                features[feature_name] = df[nhanes_var]
            else:
                logger.warning(f"Variable {nhanes_var} ({feature_name}) not found in data")
        
        # Create DataFrame
        feature_df = pd.DataFrame(features)
        
        # Add SEQN for tracking
        if 'SEQN' in df.columns:
            feature_df['SEQN'] = df['SEQN']
        
        logger.info(f"Extracted {len(feature_df.columns)} features from {len(df.columns)} raw variables")
        
        return feature_df
    
    def create_diabetes_target(self, df: pd.DataFrame) -> pd.Series:
        """
        Create binary diabetes target variable.
        
        Diabetes classification based on:
        1. Doctor diagnosis (DIQ010 = 1)
        2. HbA1c >= 6.5%
        3. Fasting glucose >= 126 mg/dL
        
        Returns:
            Binary Series: 1 = Diabetes, 0 = No Diabetes
        """
        diabetes = pd.Series(0, index=df.index, name='diabetes_status')
        
        # Doctor diagnosis
        if 'doctor_diabetes' in df.columns:
            diabetes = diabetes | (df['doctor_diabetes'] == 1)
        
        # HbA1c criterion (>= 6.5%)
        if 'hba1c' in df.columns:
            diabetes = diabetes | (df['hba1c'] >= 6.5)
        
        # Fasting glucose criterion (>= 126 mg/dL)
        if 'fasting_glucose' in df.columns:
            diabetes = diabetes | (df['fasting_glucose'] >= 126)
        
        diabetes = diabetes.astype(int)
        
        # Log statistics
        n_diabetic = diabetes.sum()
        n_total = len(diabetes)
        logger.info(f"Diabetes target: {n_diabetic} positive ({100*n_diabetic/n_total:.1f}%) out of {n_total}")
        
        return diabetes
    
    def create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create additional derived features.
        
        Args:
            df: Feature DataFrame
            
        Returns:
            DataFrame with additional derived features
        """
        df = df.copy()
        
        # Age groups (clinically relevant categories)
        if 'age' in df.columns:
            df['age_group'] = pd.cut(
                df['age'],
                bins=[0, 35, 45, 55, 65, 100],
                labels=['18-35', '36-45', '46-55', '56-65', '65+']
            )
        
        # BMI categories (WHO classification)
        if 'bmi' in df.columns:
            df['bmi_category'] = pd.cut(
                df['bmi'],
                bins=[0, 18.5, 25, 30, 35, 40, 100],
                labels=['Underweight', 'Normal', 'Overweight', 'Obese_I', 'Obese_II', 'Obese_III']
            )
        
        # Blood pressure category
        if 'systolic_bp' in df.columns and 'diastolic_bp' in df.columns:
            df['hypertension'] = (
                (df['systolic_bp'] >= 140) | (df['diastolic_bp'] >= 90)
            ).astype(int)
        
        # Smoking status (simplified)
        if 'smoked_100' in df.columns and 'current_smoker' in df.columns:
            df['smoking_status'] = 'Never'
            df.loc[df['smoked_100'] == 1, 'smoking_status'] = 'Former'
            df.loc[(df['smoked_100'] == 1) & (df['current_smoker'].isin([1, 2])), 'smoking_status'] = 'Current'
        
        # Physical activity level
        if all(col in df.columns for col in ['vigorous_work', 'moderate_work', 'vigorous_rec', 'moderate_rec']):
            activity_score = (
                (df['vigorous_work'] == 1).astype(int) * 2 +
                (df['moderate_work'] == 1).astype(int) +
                (df['vigorous_rec'] == 1).astype(int) * 2 +
                (df['moderate_rec'] == 1).astype(int)
            )
            df['activity_level'] = pd.cut(
                activity_score,
                bins=[-1, 0, 2, 4, 10],
                labels=['Sedentary', 'Low', 'Moderate', 'High']
            )
        
        return df
    
    def handle_missing_values(
        self, 
        df: pd.DataFrame,
        strategy: str = 'median'
    ) -> pd.DataFrame:
        """
        Handle missing values in the dataset.
        
        Args:
            df: Feature DataFrame
            strategy: Imputation strategy ('median', 'mean', 'most_frequent')
            
        Returns:
            DataFrame with imputed values
        """
        df = df.copy()
        
        # Log missing value summary
        missing = df.isnull().sum()
        missing_pct = 100 * missing / len(df)
        
        logger.info("Missing value summary:")
        for col in df.columns:
            if missing[col] > 0:
                logger.info(f"  {col}: {missing[col]} ({missing_pct[col]:.1f}%)")
        
        # Separate numeric and categorical columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Impute numeric columns
        if numeric_cols:
            imputer = SimpleImputer(strategy=strategy)
            df[numeric_cols] = imputer.fit_transform(df[numeric_cols])
            self.imputers['numeric'] = imputer
        
        # Impute categorical columns
        if categorical_cols:
            cat_imputer = SimpleImputer(strategy='most_frequent')
            df[categorical_cols] = cat_imputer.fit_transform(df[categorical_cols])
            self.imputers['categorical'] = cat_imputer
        
        return df
    
    def encode_categorical(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Encode categorical variables as numeric.
        
        Uses one-hot encoding for nominal variables and
        label encoding for ordinal variables.
        
        Args:
            df: Feature DataFrame
            
        Returns:
            DataFrame with encoded variables
        """
        df = df.copy()
        
        # Binary encoding for gender
        if 'gender' in df.columns:
            df['gender'] = df['gender'].map({1: 0, 2: 1})  # 0=Male, 1=Female
        
        # One-hot encode nominal categoricals
        nominal_cols = ['race_ethnicity', 'smoking_status', 'activity_level', 'bmi_category', 'age_group']
        existing_nominal = [col for col in nominal_cols if col in df.columns]
        
        if existing_nominal:
            df = pd.get_dummies(df, columns=existing_nominal, drop_first=True)
        
        return df
    
    def prepare_data(
        self,
        raw_df: pd.DataFrame,
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Full preprocessing pipeline.
        
        Args:
            raw_df: Raw merged NHANES DataFrame
            test_size: Proportion of data for testing
            random_state: Random seed for reproducibility
            
        Returns:
            Tuple of (X_train, X_test, y_train, y_test)
        """
        logger.info("Starting preprocessing pipeline...")
        
        # Step 1: Extract features
        logger.info("Step 1: Extracting features")
        df = self.extract_features(raw_df)
        
        # Step 2: Create target variable
        logger.info("Step 2: Creating target variable")
        y = self.create_diabetes_target(df)
        
        # Step 3: Create derived features
        logger.info("Step 3: Creating derived features")
        df = self.create_derived_features(df)
        
        # Step 4: Filter to valid samples (must have age >= 18)
        logger.info("Step 4: Filtering valid samples")
        valid_mask = (df['age'] >= 18) & y.notna()
        df = df[valid_mask]
        y = y[valid_mask]
        logger.info(f"Valid samples: {len(df)}")
        
        # Step 5: Handle missing values
        logger.info("Step 5: Handling missing values")
        df = self.handle_missing_values(df)
        
        # Step 6: Encode categorical variables
        logger.info("Step 6: Encoding categorical variables")
        df = self.encode_categorical(df)
        
        # Step 7: Remove non-feature columns
        exclude_cols = ['SEQN', 'doctor_diabetes', 'prediabetes', 'age_diabetes_diagnosis']
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        X = df[feature_cols]
        
        self.feature_names = feature_cols
        logger.info(f"Final feature set: {len(feature_cols)} features")
        
        # Step 8: Train/test split with stratification
        logger.info("Step 8: Train/test split")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=random_state,
            stratify=y
        )
        
        logger.info(f"Training set: {len(X_train)} samples")
        logger.info(f"Test set: {len(X_test)} samples")
        logger.info(f"Diabetes prevalence - Train: {y_train.mean():.1%}, Test: {y_test.mean():.1%}")
        
        self.is_fitted = True
        
        return X_train, X_test, y_train, y_test
    
    def save_processed_data(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
        output_dir: Optional[Path] = None
    ) -> None:
        """
        Save processed data to files.
        
        Args:
            X_train, X_test, y_train, y_test: Processed datasets
            output_dir: Output directory
        """
        output_dir = output_dir or PROCESSED_DATA_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save datasets
        X_train.to_csv(output_dir / "X_train.csv", index=False)
        X_test.to_csv(output_dir / "X_test.csv", index=False)
        y_train.to_csv(output_dir / "y_train.csv", index=False)
        y_test.to_csv(output_dir / "y_test.csv", index=False)
        
        # Save feature names
        with open(output_dir / "feature_names.txt", 'w') as f:
            f.write('\n'.join(self.feature_names))
        
        logger.info(f"Processed data saved to {output_dir}")


def main():
    """Demo of preprocessing pipeline."""
    print("\nDiabetes Preprocessor - Ready")
    print("Use with loaded NHANES data:")
    print("  preprocessor = DiabetesPreprocessor()")
    print("  X_train, X_test, y_train, y_test = preprocessor.prepare_data(raw_df)")


if __name__ == "__main__":
    main()
