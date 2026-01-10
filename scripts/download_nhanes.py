#!/usr/bin/env python3
"""
Download NHANES Data
====================
Script to download required NHANES datasets for the project.

Usage:
    python scripts/download_nhanes.py
    python scripts/download_nhanes.py --cycles 2017-2018 2015-2016
    python scripts/download_nhanes.py --force  # Re-download existing files
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ml.data import NHANESDownloader


def main():
    parser = argparse.ArgumentParser(
        description="Download NHANES datasets for health risk prediction"
    )
    parser.add_argument(
        "--cycles",
        nargs="+",
        default=["2017-2018", "2015-2016"],
        help="Survey cycles to download (default: 2017-2018 2015-2016)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download of existing files"
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=None,
        help="Specific datasets to download (default: all essential)"
    )
    
    args = parser.parse_args()
    
    # Essential datasets for diabetes model
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
    
    datasets = args.datasets or essential_datasets
    
    print("\n" + "="*60)
    print("NHANES Data Download")
    print("="*60)
    print(f"\nCycles: {', '.join(args.cycles)}")
    print(f"Datasets: {len(datasets)} selected")
    print(f"Force re-download: {args.force}")
    print()
    
    downloader = NHANESDownloader()
    results = downloader.download_all_cycles(args.cycles, datasets, args.force)
    
    # Summary
    total = 0
    successful = 0
    for cycle, cycle_results in results.items():
        for dataset, path in cycle_results.items():
            total += 1
            if path:
                successful += 1
    
    print("\n" + "="*60)
    print(f"Complete: {successful}/{total} files downloaded successfully")
    print("="*60)


if __name__ == "__main__":
    main()
