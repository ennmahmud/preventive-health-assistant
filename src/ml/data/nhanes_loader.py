"""
NHANES Data Loader
==================
Loads and processes NHANES XPT files into pandas DataFrames.

Handles:
- Reading SAS Transport (.XPT) format files
- Merging datasets by respondent ID (SEQN)
- Initial data cleaning and validation
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config import PROCESSED_DATA_DIR, RAW_DATA_DIR

logger = logging.getLogger(__name__)


class NHANESLoader:
    """
    Loads NHANES datasets from XPT files.

    NHANES data uses SEQN (Respondent Sequence Number) as the primary key
    to link data across different datasets.

    Example:
        >>> loader = NHANESLoader()
        >>> demo_df = loader.load_dataset("2017-2018", "DEMO")
        >>> merged_df = loader.load_and_merge("2017-2018", ["DEMO", "BMX", "GHB"])
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the loader.

        Args:
            data_dir: Directory containing raw NHANES data
        """
        self.data_dir = data_dir or RAW_DATA_DIR
        logger.info(f"NHANES Loader initialized. Data directory: {self.data_dir}")

    def _find_xpt_file(self, cycle: str, dataset_code: str) -> Optional[Path]:
        """
        Find the XPT file for a given cycle and dataset.

        Args:
            cycle: Survey cycle (e.g., "2017-2018")
            dataset_code: Dataset code (e.g., "DEMO")

        Returns:
            Path to XPT file, or None if not found
        """
        cycle_dir = self.data_dir / cycle.replace("-", "_")

        if not cycle_dir.exists():
            logger.warning(f"Cycle directory not found: {cycle_dir}")
            return None

        # Look for matching files
        pattern = f"{dataset_code}*.XPT"
        matches = list(cycle_dir.glob(pattern))

        if not matches:
            # Try lowercase
            pattern_lower = f"{dataset_code}*.xpt"
            matches = list(cycle_dir.glob(pattern_lower))

        if matches:
            return matches[0]

        logger.warning(f"No file found for {dataset_code} in {cycle}")
        return None

    def load_dataset(
        self, cycle: str, dataset_code: str, columns: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        """
        Load a single NHANES dataset.

        Args:
            cycle: Survey cycle (e.g., "2017-2018")
            dataset_code: Dataset code (e.g., "DEMO")
            columns: Optional list of columns to load. If None, loads all.

        Returns:
            DataFrame with dataset, or None if loading failed
        """
        file_path = self._find_xpt_file(cycle, dataset_code)

        if file_path is None:
            return None

        try:
            logger.info(f"Loading: {file_path}")

            # Check file size
            file_size = file_path.stat().st_size
            if file_size < 1024:
                logger.error(f"File too small ({file_size} bytes), likely corrupted: {file_path}")
                logger.error("Try running: python scripts/download_nhanes.py --force")
                return None

            # Use pandas read_sas which handles XPT format well
            df = pd.read_sas(file_path, format="xport")

            # Select columns if specified
            if columns:
                available_cols = [c for c in columns if c in df.columns]
                if available_cols:
                    df = df[available_cols]

            logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns from {dataset_code}")

            # Store metadata as attribute
            df.attrs["nhanes_metadata"] = {
                "cycle": cycle,
                "dataset": dataset_code,
                "source_file": str(file_path),
            }

            return df

        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            logger.error(f"File size: {file_path.stat().st_size} bytes")
            logger.error(
                "The file may be corrupted. Try: python scripts/download_nhanes.py --force"
            )
            return None

    def load_and_merge(
        self, cycle: str, dataset_codes: List[str], merge_on: str = "SEQN"
    ) -> Optional[pd.DataFrame]:
        """
        Load and merge multiple NHANES datasets.

        All NHANES datasets share the SEQN column which uniquely identifies
        survey respondents, allowing datasets to be merged.

        Args:
            cycle: Survey cycle
            dataset_codes: List of dataset codes to load and merge
            merge_on: Column to merge on (default: SEQN)

        Returns:
            Merged DataFrame, or None if any dataset failed to load
        """
        if not dataset_codes:
            logger.error("No datasets specified")
            return None

        # Load first dataset
        merged_df = self.load_dataset(cycle, dataset_codes[0])

        if merged_df is None:
            return None

        # Merge remaining datasets
        for code in dataset_codes[1:]:
            df = self.load_dataset(cycle, code)

            if df is None:
                logger.warning(f"Skipping {code} - failed to load")
                continue

            # Merge on SEQN (outer join to preserve all respondents)
            merged_df = pd.merge(merged_df, df, on=merge_on, how="outer", suffixes=("", f"_{code}"))

            logger.info(f"After merging {code}: {len(merged_df)} rows")

        return merged_df

    def load_multiple_cycles(
        self, cycles: List[str], dataset_codes: List[str]
    ) -> Optional[pd.DataFrame]:
        """
        Load and combine data from multiple survey cycles.

        Useful for increasing sample size by combining multiple years of data.

        Args:
            cycles: List of survey cycles
            dataset_codes: List of dataset codes

        Returns:
            Combined DataFrame with cycle indicator column
        """
        all_data = []

        for cycle in cycles:
            logger.info(f"\nProcessing cycle: {cycle}")
            df = self.load_and_merge(cycle, dataset_codes)

            if df is not None:
                df["survey_cycle"] = cycle
                all_data.append(df)

        if not all_data:
            logger.error("No data loaded from any cycle")
            return None

        combined = pd.concat(all_data, ignore_index=True)
        logger.info(f"Combined data: {len(combined)} total rows from {len(all_data)} cycles")

        return combined

    def get_dataset_info(self, cycle: str, dataset_code: str) -> Dict:
        """
        Get metadata information about a dataset.

        Args:
            cycle: Survey cycle
            dataset_code: Dataset code

        Returns:
            Dictionary with dataset metadata
        """
        df = self.load_dataset(cycle, dataset_code)

        if df is None:
            return {"error": "Failed to load dataset"}

        info = {
            "cycle": cycle,
            "dataset": dataset_code,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "missing_counts": df.isnull().sum().to_dict(),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
        }

        # Add NHANES metadata if available
        if "nhanes_metadata" in df.attrs:
            info["nhanes_metadata"] = df.attrs["nhanes_metadata"]

        return info


def main():
    """Demo of NHANES data loading."""
    loader = NHANESLoader()

    # Check what data is available
    print("\nChecking available data...")

    cycles = ["2017_2018", "2015_2016"]

    for cycle in cycles:
        cycle_dir = loader.data_dir / cycle
        if cycle_dir.exists():
            files = list(cycle_dir.glob("*.XPT")) + list(cycle_dir.glob("*.xpt"))
            print(f"\n{cycle}: {len(files)} files")
            for f in files:
                print(f"  - {f.name} ({f.stat().st_size / 1024:.1f} KB)")
        else:
            print(f"\n{cycle}: Directory not found")


if __name__ == "__main__":
    main()
