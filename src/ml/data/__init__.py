"""
Data Module
===========
Data acquisition, loading, and preprocessing for NHANES datasets.
"""

from .nhanes_downloader import NHANESDownloader, DIABETES_DATASETS
from .nhanes_loader import NHANESLoader
from .diabetes_preprocessor import DiabetesPreprocessor

__all__ = [
    "NHANESDownloader",
    "NHANESLoader",
    "DiabetesPreprocessor",
    "DIABETES_DATASETS",
]
