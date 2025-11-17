"""
Master Pipeline Execution Script
=================================

Runs the complete "Where to DINE" data processing pipeline.

Execution Order:
1. Phase 2: Process taxi data with temporal filtering
2. Phase 3: Merge and deduplicate restaurants
3. Phase 6: Cluster restaurants (HDBSCAN)
4. Phase 7: Cluster taxi dropoffs (HDBSCAN)
5. Phase 8: Spatial intersection for final hotspots

Author: Where to DINE Project
Date: 2025-11-09
"""

import subprocess
import sys
import logging
from pathlib import Path
import time
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_script(script_path: str, phase_name: str) -> bool:
    """
    Run a Python script and capture output.

    Parameters:
    -----------
    script_path : str
        Path to the Python script
    phase_name : str
        Human-readable phase name

    Returns:
    --------
    bool
        True if successful, False otherwise
    """
    logger.info("="*80)
    logger.info(f"STARTING: {phase_name}")
    logger.info(f"Script: {script_path}")
    logger.info("="*80)

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=False,  # Show output in real-time
            text=True
        )

        elapsed_time = time.time() - start_time

        logger.info("="*80)
        logger.info(f"✅ COMPLETED: {phase_name}")
        logger.info(f"Time elapsed: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
        logger.info("="*80)
        logger.info("")

        return True

    except subprocess.CalledProcessError as e:
        elapsed_time = time.time() - start_time

        logger.error("="*80)
        logger.error(f"❌ FAILED: {phase_name}")
        logger.error(f"Time elapsed: {elapsed_time:.1f} seconds")
        logger.error(f"Error: {e}")
        logger.error("="*80)
        logger.error("")

        return False


def check_prerequisites():
    """
    Check if all required data files exist before starting.
    """
    logger.info("Checking prerequisites...")

    required_files = [
        "config/config.yaml",
        "data/external/boundaries/nybb.shp"
    ]

    required_dirs = [
        "data/raw/taxi",
        "data/raw/restaurants"
    ]

    missing = []

    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(f"File: {file_path}")

    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            missing.append(f"Directory: {dir_path}")
        elif not any(path.iterdir()):
            missing.append(f"Directory (empty): {dir_path}")

    if missing:
        logger.error("❌ Missing prerequisites:")
        for item in missing:
            logger.error(f"  - {item}")
        logger.error("\nPlease ensure all required data files are in place before running the pipeline.")
        return False

    logger.info("✅ All prerequisites satisfied")
    return True


def main():
    """
    Main execution function.
    """
    start_time = datetime.now()

    logger.info("")
    logger.info("="*80)
    logger.info("WHERE TO DINE - COMPLETE DATA PROCESSING PIPELINE")
    logger.info("="*80)
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # Define pipeline phases
    phases = [
        {
            'script': 'src/data_processing/02_process_taxi_data.py',
            'name': 'Phase 2: Taxi Data Processing',
            'description': 'Filter taxi data to dining hours and apply temporal weights'
        },
        {
            'script': 'src/data_processing/02_merge_restaurants.py',
            'name': 'Phase 3: Restaurant Data Merging',
            'description': 'Merge Google Maps and OSM restaurants, remove duplicates'
        },
        {
            'script': 'src/data_processing/06_cluster_restaurants.py',
            'name': 'Phase 6: Restaurant Clustering',
            'description': 'Apply HDBSCAN to identify dining zones'
        },
        {
            'script': 'src/data_processing/07_cluster_taxi_dropoffs.py',
            'name': 'Phase 7: Taxi Clustering',
            'description': 'Apply HDBSCAN to identify taxi hotspots'
        },
        {
            'script': 'src/data_processing/08_spatial_intersection.py',
            'name': 'Phase 8: Spatial Intersection',
            'description': 'Identify final dining hotspots from intersection'
        }
    ]

    # Execute pipeline
    results = []

    for i, phase in enumerate(phases, 1):
        logger.info(f"\n[{i}/{len(phases)}] {phase['name']}")
        logger.info(f"Description: {phase['description']}\n")

        success = run_script(phase['script'], phase['name'])
        results.append({
            'phase': phase['name'],
            'success': success
        })

        if not success:
            logger.error(f"\n❌ Pipeline failed at {phase['name']}")
            logger.error("Please check the error messages above and fix the issue.")
            logger.error("You can re-run the pipeline from this point after fixing the error.")
            sys.exit(1)

        # Brief pause between phases
        time.sleep(1)

    # Final summary
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()

    logger.info("\n" + "="*80)
    logger.info("PIPELINE EXECUTION SUMMARY")
    logger.info("="*80)
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    logger.info("")
    logger.info("Phase Results:")

    all_success = True
    for i, result in enumerate(results, 1):
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        logger.info(f"  {i}. {result['phase']}: {status}")
        if not result['success']:
            all_success = False

    logger.info("="*80)

    if all_success:
        logger.info("\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info("\nNext steps:")
        logger.info("  1. Check outputs in data/processed/")
        logger.info("  2. Review final_hotspots.geojson for dining recommendations")
        logger.info("  3. Run visualization scripts to create maps")
        logger.info("  4. (Optional) Run network analysis for accessibility scoring")
    else:
        logger.error("\n❌ PIPELINE FAILED")
        logger.error("Please review error messages above.")

    logger.info("")


if __name__ == "__main__":
    main()
