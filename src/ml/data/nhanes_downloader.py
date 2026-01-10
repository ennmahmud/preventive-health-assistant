"""
NHANES Data Downloader
======================
Downloads NHANES datasets from CDC for health risk prediction models.

NHANES (National Health and Nutrition Examination Survey) provides
nationally representative health data used for training our models.

Data Source: https://www.cdc.gov/nchs/nhanes/index.htm
"""

import logging

# import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# import pandas as pd
import requests
from tqdm import tqdm

# from typing import Dict, List, Optional, Tuple


# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# from config import NHANES_CONFIG, RAW_DATA_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NHANESCycle(Enum):
    """Available NHANES survey cycles."""

    CYCLE_2017_2018 = "2017-2018"
    CYCLE_2019_2020 = "2019-2020"  # Note: Affected by COVID-19
    CYCLE_2021_2022 = "2021-2022"

    # Pre-pandemic cycles for more complete data
    CYCLE_2015_2016 = "2015-2016"
    CYCLE_2013_2014 = "2013-2014"


@dataclass
class DatasetInfo:
    """Information about a specific NHANES dataset."""

    name: str
    code: str
    description: str
    category: str  # 'demographics', 'examination', 'laboratory', 'questionnaire'


# Comprehensive dataset definitions for diabetes and CVD prediction
DIABETES_DATASETS: dict[str, DatasetInfo] = {
    "demographics": DatasetInfo(
        name="Demographic Variables",
        code="DEMO",
        description="Age, gender, race/ethnicity, education, income",
        category="demographics",
    ),
    "body_measures": DatasetInfo(
        name="Body Measures",
        code="BMX",
        description="BMI, weight, height, waist circumference",
        category="examination",
    ),
    "blood_pressure": DatasetInfo(
        name="Blood Pressure",
        code="BPX",
        description="Systolic and diastolic blood pressure measurements",
        category="examination",
    ),
    "glycohemoglobin": DatasetInfo(
        name="Glycohemoglobin (HbA1c)",
        code="GHB",
        description="Glycated hemoglobin for diabetes assessment",
        category="laboratory",
    ),
    "plasma_glucose": DatasetInfo(
        name="Plasma Fasting Glucose",
        code="GLU",
        description="Fasting glucose and insulin levels",
        category="laboratory",
    ),
    "cholesterol_total": DatasetInfo(
        name="Total Cholesterol",
        code="TCHOL",
        description="Total cholesterol levels",
        category="laboratory",
    ),
    "cholesterol_hdl": DatasetInfo(
        name="HDL Cholesterol",
        code="HDL",
        description="HDL (good) cholesterol levels",
        category="laboratory",
    ),
    "diabetes_questionnaire": DatasetInfo(
        name="Diabetes Questionnaire",
        code="DIQ",
        description="Self-reported diabetes status, family history",
        category="questionnaire",
    ),
    "medical_conditions": DatasetInfo(
        name="Medical Conditions",
        code="MCQ",
        description="History of medical conditions including heart disease",
        category="questionnaire",
    ),
    "smoking": DatasetInfo(
        name="Smoking Status",
        code="SMQ",
        description="Cigarette smoking history and current use",
        category="questionnaire",
    ),
    "alcohol": DatasetInfo(
        name="Alcohol Use",
        code="ALQ",
        description="Alcohol consumption patterns",
        category="questionnaire",
    ),
    "physical_activity": DatasetInfo(
        name="Physical Activity",
        code="PAQ",
        description="Physical activity levels and sedentary behavior",
        category="questionnaire",
    ),
}


class NHANESDownloader:
    """
    Downloads NHANES datasets from CDC servers.

    NHANES data is provided in SAS Transport (.XPT) format.
    This class handles downloading and converting to pandas DataFrames.

    Example:
        >>> downloader = NHANESDownloader()
        >>> downloader.download_cycle("2017-2018", ["demographics", "glycohemoglobin"])
    """

    # New CDC URL structure (changed in recent years)
    BASE_URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes"

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the downloader.

        Args:
            output_dir: Directory to save downloaded files. Defaults to data/raw.
        """
        self.output_dir = output_dir or RAW_DATA_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"NHANES Downloader initialized. Output directory: {self.output_dir}")

    def _get_file_url(self, cycle: str, dataset_code: str) -> str:
        """
        Construct the URL for a specific NHANES dataset file.

        CDC URL structure (as of 2024):
        https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{start_year}/DataFiles/{CODE}_{SUFFIX}.xpt

        NHANES naming convention varies by cycle:
        - 2017-2018: DEMO_J.xpt (suffix _J)
        - 2015-2016: DEMO_I.xpt (suffix _I)
        - 2013-2014: DEMO_H.xpt (suffix _H)

        Args:
            cycle: Survey cycle (e.g., "2017-2018")
            dataset_code: Dataset code (e.g., "DEMO")

        Returns:
            Full URL to the XPT file
        """
        # Cycle suffix and start year mapping
        cycle_info = {
            "2013-2014": {"suffix": "_H", "year": "2013"},
            "2015-2016": {"suffix": "_I", "year": "2015"},
            "2017-2018": {"suffix": "_J", "year": "2017"},
            "2019-2020": {"suffix": "_K", "year": "2019"},
            "2021-2022": {"suffix": "_L", "year": "2021"},
        }

        info = cycle_info.get(cycle, {"suffix": "_J", "year": "2017"})
        suffix = info["suffix"]
        year = info["year"]

        # Note: CDC uses lowercase .xpt extension in new URL structure
        filename = f"{dataset_code}{suffix}.xpt"

        return f"{self.BASE_URL}/{year}/DataFiles/{filename}"

    def _download_file(self, url: str, output_path: Path) -> bool:
        """
        Download a single file from URL.

        Args:
            url: URL to download from
            output_path: Local path to save file

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading: {url}")
            response = requests.get(url, stream=True, timeout=120)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))

            with open(output_path, "wb") as f:
                with tqdm(
                    total=total_size, unit="B", unit_scale=True, desc=output_path.name
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

            # Verify file was downloaded correctly
            if not self._validate_xpt_file(output_path):
                logger.error(f"Downloaded file is invalid: {output_path}")
                output_path.unlink()  # Delete corrupted file
                return False

            logger.info(f"Successfully downloaded: {output_path.name}")
            return True

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"File not found (404): {url}")
                # Try alternative naming for 2019-2020 pre-pandemic data
                return False
            logger.error(f"HTTP error downloading {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return False

    def _validate_xpt_file(self, filepath: Path) -> bool:
        """
        Validate that an XPT file is valid.

        XPT files (SAS Transport format) should start with "HEADER RECORD"
        and be at least a few KB in size.

        Args:
            filepath: Path to XPT file

        Returns:
            True if file appears valid
        """
        try:
            # Check file size (should be at least 1KB for any real data)
            if filepath.stat().st_size < 1024:
                logger.warning(f"File too small: {filepath}")
                return False

            # Check XPT header - should start with "HEADER RECORD"
            with open(filepath, "rb") as f:
                header = f.read(80)
                if b"HEADER RECORD" not in header:
                    logger.warning(f"Invalid XPT header: {filepath}")
                    return False

            return True
        except Exception as e:
            logger.error(f"Error validating file {filepath}: {e}")
            return False

    def download_dataset(self, cycle: str, dataset_key: str, force: bool = False) -> Optional[Path]:
        """
        Download a specific dataset for a given cycle.

        Args:
            cycle: Survey cycle (e.g., "2017-2018")
            dataset_key: Key from DIABETES_DATASETS (e.g., "demographics")
            force: If True, re-download even if file exists

        Returns:
            Path to downloaded file, or None if failed
        """
        if dataset_key not in DIABETES_DATASETS:
            logger.error(f"Unknown dataset: {dataset_key}")
            return None

        dataset_info = DIABETES_DATASETS[dataset_key]

        # Create cycle-specific directory
        cycle_dir = self.output_dir / cycle.replace("-", "_")
        cycle_dir.mkdir(parents=True, exist_ok=True)

        # Output filename
        output_path = cycle_dir / f"{dataset_info.code}_{cycle.replace('-', '_')}.XPT"

        # Check if file exists and is valid
        if output_path.exists() and not force:
            if self._validate_xpt_file(output_path):
                logger.info(f"File already exists and is valid: {output_path}")
                return output_path
            else:
                logger.warning(f"Existing file is invalid, re-downloading: {output_path}")
                output_path.unlink()  # Delete corrupted file

        # Download
        url = self._get_file_url(cycle, dataset_info.code)
        success = self._download_file(url, output_path)

        if not success:
            # Try alternative URL patterns for 2019-2020
            if cycle == "2019-2020":
                alt_url = f"{self.BASE_URL}/{cycle}/P_{dataset_info.code}.XPT"
                logger.info(f"Trying alternative URL: {alt_url}")
                success = self._download_file(alt_url, output_path)

        return output_path if success else None

    def download_cycle(
        self, cycle: str, datasets: Optional[List[str]] = None, force: bool = False
    ) -> Dict[str, Optional[Path]]:
        """
        Download multiple datasets for a survey cycle.

        Args:
            cycle: Survey cycle (e.g., "2017-2018")
            datasets: List of dataset keys to download. If None, downloads all.
            force: If True, re-download even if files exist

        Returns:
            Dictionary mapping dataset keys to file paths
        """
        if datasets is None:
            datasets = list(DIABETES_DATASETS.keys())

        logger.info(f"Downloading {len(datasets)} datasets for cycle {cycle}")

        results = {}
        for dataset_key in datasets:
            results[dataset_key] = self.download_dataset(cycle, dataset_key, force)

        # Summary
        successful = sum(1 for v in results.values() if v is not None)
        logger.info(f"Download complete: {successful}/{len(datasets)} datasets successful")

        return results

    def download_all_cycles(
        self,
        cycles: Optional[List[str]] = None,
        datasets: Optional[List[str]] = None,
        force: bool = False,
    ) -> Dict[str, Dict[str, Optional[Path]]]:
        """
        Download datasets for multiple survey cycles.

        Args:
            cycles: List of cycles to download. If None, uses default cycles.
            datasets: List of dataset keys. If None, downloads all.
            force: If True, re-download even if files exist

        Returns:
            Nested dictionary: cycle -> dataset -> path
        """
        if cycles is None:
            cycles = ["2017-2018", "2015-2016", "2013-2014"]  # Pre-pandemic cycles

        all_results = {}
        for cycle in cycles:
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing cycle: {cycle}")
            logger.info(f"{'='*50}")
            all_results[cycle] = self.download_cycle(cycle, datasets, force)

        return all_results


def main():
    """Main function to download NHANES data for the project."""
    print("\n" + "=" * 60)
    print("NHANES Data Acquisition for Preventive Health Assistant")
    print("=" * 60 + "\n")

    downloader = NHANESDownloader()

    # Download key datasets for diabetes prediction
    # Using pre-pandemic cycles for more complete data
    cycles = ["2017-2018", "2015-2016"]

    # Essential datasets for diabetes risk model
    essential_datasets = [
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

    print(f"Downloading {len(essential_datasets)} datasets for {len(cycles)} cycles...")
    print(f"Datasets: {', '.join(essential_datasets)}")
    print(f"Cycles: {', '.join(cycles)}\n")

    results = downloader.download_all_cycles(cycles, essential_datasets)

    # Print summary
    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)

    for cycle, datasets in results.items():
        print(f"\n{cycle}:")
        for dataset, path in datasets.items():
            status = "✓" if path else "✗"
            print(f"  {status} {dataset}")

    print("\nData acquisition complete!")
    print(f"Files saved to: {RAW_DATA_DIR}")


if __name__ == "__main__":
    main()
