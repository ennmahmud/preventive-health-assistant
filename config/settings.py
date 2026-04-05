"""
Project Configuration
=====================
Central configuration for the Preventive Health Assistant project.
"""

from pathlib import Path
from typing import Dict, List
import os

# Project Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"
MODELS_DIR = PROJECT_ROOT / "models" / "saved"

# Ensure directories exist
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, EXTERNAL_DATA_DIR, MODELS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# NHANES Configuration
NHANES_CONFIG = {
    "base_url": "https://wwwn.cdc.gov/Nchs/Nhanes",
    "cycles": ["2017-2018", "2019-2020", "2021-2022"],  # Recent cycles with consistent variables
    "datasets": {
        "demographics": "DEMO",
        "diabetes": "DIQ",           # Diabetes questionnaire
        "glucose": "GLU",            # Fasting glucose & insulin
        "glycohemoglobin": "GHB",    # HbA1c
        "body_measures": "BMX",      # BMI, waist circumference
        "blood_pressure": "BPX",     # Blood pressure
        "cholesterol_total": "TCHOL", # Total cholesterol
        "cholesterol_hdl": "HDL",    # HDL cholesterol
        "questionnaire_medical": "MCQ",  # Medical conditions questionnaire
        "smoking": "SMQ",            # Smoking questionnaire
        "alcohol": "ALQ",            # Alcohol use
        "physical_activity": "PAQ",  # Physical activity
        "diet_behavior": "DBQ",      # Diet behavior
    }
}

# Diabetes Risk Model Configuration
DIABETES_CONFIG = {
    "target_variable": "diabetes_status",
    "features": {
        "demographic": ["age", "gender", "race_ethnicity", "education", "income_ratio"],
        "anthropometric": ["bmi", "waist_circumference"],
        "clinical": ["systolic_bp", "diastolic_bp", "total_cholesterol", "hdl_cholesterol", "hba1c"],
        "lifestyle": ["smoking_status", "alcohol_use", "physical_activity_level"],
        "family_history": ["family_diabetes"],
    },
    "model_params": {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "eval_metric": "auc",
        "early_stopping_rounds": 20,
    },
    "validation": {
        "test_size": 0.2,
        "cv_folds": 5,
        "target_accuracy": 0.80,
        "target_auc": 0.80,
    }
}

# Cardiovascular Disease Risk Model Configuration
CVD_CONFIG = {
    "target_variable": "cvd_status",
    "features": {
        "demographic": ["age", "gender", "race_ethnicity"],
        "anthropometric": ["bmi", "waist_circumference"],
        "clinical": ["systolic_bp", "diastolic_bp", "total_cholesterol", "hdl_cholesterol", "fasting_glucose"],
        "lifestyle": ["smoking_status", "alcohol_use", "physical_activity_level"],
        "medical_history": ["diabetes_status", "hypertension_status"],
    },
    "model_params": {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "eval_metric": "auc",
        "early_stopping_rounds": 20,
    },
    "validation": {
        "test_size": 0.2,
        "cv_folds": 5,
        "target_accuracy": 0.80,
        "target_auc": 0.80,
    }
}

# Hypertension Risk Model Configuration
HYPERTENSION_CONFIG = {
    "target_variable": "hypertension_status",
    "features": {
        "demographic": ["age", "gender", "race_ethnicity", "education", "income_ratio"],
        "anthropometric": ["bmi", "waist_circumference"],
        "clinical": ["total_cholesterol", "hdl_cholesterol", "hba1c", "fasting_glucose"],
        "lifestyle": ["smoking_status", "alcohol_use", "physical_activity_level"],
        "derived": ["diabetes_indicator"],
        # NOTE: blood pressure readings are EXCLUDED to avoid circularity
        # (BP readings are used to DEFINE the target, not predict it)
    },
    "model_params": {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "eval_metric": "auc",
        "early_stopping_rounds": 20,
    },
    "validation": {
        "test_size": 0.2,
        "cv_folds": 5,
        "target_accuracy": 0.75,  # Slightly lower target — harder without BP as feature
        "target_auc": 0.78,
    },
}

# API Configuration
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": os.getenv("DEBUG", "False").lower() == "true",
    "cors_origins": [
        "http://localhost:3000",    # React CRA dev server
        "http://127.0.0.1:3000",
        "http://localhost:5173",    # Vite dev server
        "http://127.0.0.1:5173",
    ],
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    "rotation": "10 MB",
    "retention": "30 days",
}
