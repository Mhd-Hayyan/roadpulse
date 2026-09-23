"""
ROADPULSE — Feature Extraction Validation Test Suite
=====================================================
Validates that:
  1. Preprocessed data loads properly.
  2. Feature extraction executes without error.
  3. Feature output is non-empty.
  4. All expected feature columns exist.
  5. Ground-truth columns are completely absent from the feature set.
  6. No NaN or infinite values exist in any feature column.
  7. Multiple passes are represented.
  8. Windows do not cross pass boundaries.
  9. Window duration is approximately 0.48–0.50 seconds.
 10. All numerical values are valid finite floats.
 11. Total rows are substantially fewer than raw 12,200 samples (window compression).
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.features import (
    INPUT_DATA_PATH,
    OUTPUT_FEATURES_PATH,
    load_preprocessed_data,
    extract_dataset_features,
)

EXPECTED_FEATURE_COLUMNS = [
    # Metadata
    "pass_id", "window_start", "window_end", "window_duration",
    # Vertical features
    "accel_z_mean", "accel_z_std", "accel_z_min", "accel_z_max",
    "accel_z_peak_to_peak", "accel_z_rms", "accel_z_energy",
    "accel_z_max_abs", "accel_z_max_abs_diff",
    # Longitudinal features
    "accel_y_mean", "accel_y_std", "accel_y_min", "accel_y_max",
    "accel_y_rms", "accel_y_max_abs",
    # Lateral features
    "accel_x_mean", "accel_x_std", "accel_x_min", "accel_x_max",
    "accel_x_rms", "accel_x_max_abs",
    # Gyroscope features
    "gyro_x_mean", "gyro_x_std", "gyro_x_max_abs",
    "gyro_y_mean", "gyro_y_std", "gyro_y_max_abs",
    "gyro_z_mean", "gyro_z_std", "gyro_z_max_abs",
    "gyro_mag_mean", "gyro_mag_max",
    # GPS features
    "gps_lat_start", "gps_lon_start",
    "gps_lat_end", "gps_lon_end",
    "gps_displacement",
]


def _check(label, condition, detail=""):
    icon = "[PASS]" if condition else "[FAIL]"
    line = f"  {icon}  {label}"
    if not condition and detail:
        line += f"  -  {detail}"
    print(line)
    return condition


def run():
    results = []

    print("\n==================================================")
    print("  ROADPULSE -- Feature Extraction Validation")
    print("==================================================")

    # 1. Load preprocessed data
    can_load = False
    preproc_df = None
    try:
        preproc_df = load_preprocessed_data(INPUT_DATA_PATH)
        can_load = isinstance(preproc_df, pd.DataFrame) and len(preproc_df) > 0
    except Exception as e:
        can_load = False

    results.append(_check("Preprocessed dataset loads successfully", can_load))
    if not can_load:
        print("\n[FATAL] Unable to load preprocessed dataset. Exiting test.")
        sys.exit(1)

    # 2. Run feature extraction
    try:
        features_df = extract_dataset_features(preproc_df)
        extraction_success = isinstance(features_df, pd.DataFrame) and len(features_df) > 0
    except Exception as e:
        extraction_success = False

    results.append(_check("Feature extraction runs successfully", extraction_success))
    if not extraction_success:
        print("\n[FATAL] Feature extraction failed. Exiting test.")
        sys.exit(1)

    # 3. Output is not empty
    results.append(_check(
        f"Feature output is non-empty ({len(features_df)} windows)",
        len(features_df) > 0,
    ))

    # 4. Expected feature columns exist
    missing_cols = set(EXPECTED_FEATURE_COLUMNS) - set(features_df.columns)
    results.append(_check(
        "All expected feature columns exist",
        len(missing_cols) == 0,
        f"missing: {missing_cols}",
    ))

    # 5. Strict ground-truth isolation
    gt_columns = ["ground_truth_event", "ground_truth_type"]
    found_gt = [c for c in gt_columns if c in features_df.columns]
    results.append(_check(
        "Ground truth columns are completely absent",
        len(found_gt) == 0,
        f"forbidden columns found: {found_gt}",
    ))

    # 6. No unexpected NaN or infinite values
    has_nan_or_inf = False
    numeric_cols = features_df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if features_df[col].isna().any() or np.isinf(features_df[col]).any():
            has_nan_or_inf = True
            break
    results.append(_check("No NaN or infinite values in feature columns", not has_nan_or_inf))

    # 7. Multiple passes are represented
    passes = features_df["pass_id"].unique()
    results.append(_check(
        "Multiple passes represented (all 4 passes)",
        len(passes) == 4 and set(passes) == {1, 2, 3, 4},
        f"passes found: {passes}",
    ))

    # 8. Windows do not cross pass boundaries
    # Within each pass, timestamps should be ordered and window_start < window_end
    no_crossing = True
    for pid, grp in features_df.groupby("pass_id"):
        if not (grp["window_start"] < grp["window_end"]).all():
            no_crossing = False
            break
        diffs = np.diff(grp["window_start"].values)
        if not (diffs > 0).all():
            no_crossing = False
            break
    results.append(_check("Windows do not cross pass boundaries and are strictly ordered", no_crossing))

    # 9. Window duration approximately 0.48–0.50 s (25 samples at 50 Hz = 24 * 0.02 = 0.48 s span)
    mean_duration = float(features_df["window_duration"].mean())
    duration_ok = 0.45 <= mean_duration <= 0.55
    results.append(_check(
        f"Window duration approximately correct (mean: {mean_duration:.3f} s)",
        duration_ok,
    ))

    # 10. All numeric features are finite numbers
    all_finite = np.all(np.isfinite(features_df[numeric_cols].values))
    results.append(_check("All numerical feature values are finite numbers", all_finite))

    # 11. Substantially fewer rows than raw 12,200
    is_compressed = len(features_df) < len(preproc_df) * 0.25
    results.append(_check(
        f"Dataset compressed from {len(preproc_df):,} samples to {len(features_df):,} windows",
        is_compressed,
    ))

    # Summary
    n_passed = sum(results)
    n_failed = len(results) - n_passed

    print("==================================================")
    print(f"  Result   : {n_passed} passed,  {n_failed} failed")
    print(f"  Windows  : {len(features_df):,}")
    print(f"  Columns  : {len(features_df.columns)}")
    print("==================================================\n")

    if n_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run()
