"""Configuration module for Preventive Health Assistant."""

from .settings import (
    PROJECT_ROOT,
    DATA_DIR,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    EXTERNAL_DATA_DIR,
    MODELS_DIR,
    NHANES_CONFIG,
    DIABETES_CONFIG,
    CVD_CONFIG,
    API_CONFIG,
    LOGGING_CONFIG,
)

__all__ = [
    "PROJECT_ROOT",
    "DATA_DIR",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "EXTERNAL_DATA_DIR",
    "MODELS_DIR",
    "NHANES_CONFIG",
    "DIABETES_CONFIG",
    "CVD_CONFIG",
    "API_CONFIG",
    "LOGGING_CONFIG",
]
