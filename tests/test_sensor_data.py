"""
ROADPULSE — Sensor Data Validation
====================================
Validates the structure and sanity of  data/raw/sensor_data.csv.

Run with:
    python tests/test_sensor_data.py

What this script checks
-----------------------
  1. The CSV file exists
  2. All 12 expected columns are present
  3. At least 3 passes are present
  4. Timestamps are monotonically increasing within every pass
  5. All required ground_truth_type labels appear in the dataset
  6. Mean sample interval ≈ 0.02 s  (50 Hz)  for each pass
  7. No NaN values in any sensor column
  8. GPS coordinates fall within the Kerala bounding box
  9. Dataset contains more than 1,000 rows
 10. ground_truth_event contains only 0 or 1 (binary flag)

Important: ground-truth columns are only checked for STRUCTURAL correctness.
This script does NOT use them for any kind of event detection.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

# ─── Paths and expected values ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH     = PROJECT_ROOT / "data" / "raw" / "sensor_data.csv"

EXPECTED_COLUMNS = [
    "timestamp", "pass_id", "latitude", "longitude",
    "accel_x", "accel_y", "accel_z",
    "gyro_x",  "gyro_y",  "gyro_z",
    "ground_truth_event", "ground_truth_type",
]

# Every label that should appear at least once in the dataset
EXPECTED_GT_TYPES = {
    "none", "pothole", "speed_breaker",
    "rough_road", "braking", "turning", "acceleration",
}

SAMPLE_INTERVAL    = 1.0 / 50    # 0.02 s  — 50 Hz
INTERVAL_TOLERANCE = 0.001       # ±1 ms tolerance
MIN_PASSES         = 3


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _check(label, condition, detail=""):
    """Print a pass/fail line and return the boolean result."""
    icon = "[PASS]" if condition else "[FAIL]"
    line = f"  {icon}  {label}"
    if not condition and detail:
        line += f"  -  {detail}"
    print(line)
    return condition


# ─── Pytest-compatible individual test functions ──────────────────────────────

def test_csv_file_exists():
    assert CSV_PATH.exists()

def test_all_expected_columns_present():
    df = pd.read_csv(CSV_PATH)
    assert set(EXPECTED_COLUMNS).issubset(set(df.columns))

def test_minimum_passes_present():
    df = pd.read_csv(CSV_PATH)
    assert df["pass_id"].nunique() >= MIN_PASSES

def test_timestamps_monotonically_increasing():
    df = pd.read_csv(CSV_PATH)
    for _, grp in df.groupby("pass_id"):
        diffs = np.diff(grp["timestamp"].values)
        assert np.all(diffs > 0)

def test_all_required_ground_truth_labels_present():
    df = pd.read_csv(CSV_PATH)
    assert EXPECTED_GT_TYPES.issubset(set(df["ground_truth_type"].unique()))

def test_sampling_interval_pass_1():
    df = pd.read_csv(CSV_PATH)
    diffs = np.diff(df[df["pass_id"] == 1]["timestamp"].values)
    assert abs(diffs.mean() - SAMPLE_INTERVAL) < INTERVAL_TOLERANCE

def test_sampling_interval_pass_2():
    df = pd.read_csv(CSV_PATH)
    diffs = np.diff(df[df["pass_id"] == 2]["timestamp"].values)
    assert abs(diffs.mean() - SAMPLE_INTERVAL) < INTERVAL_TOLERANCE

def test_sampling_interval_pass_3():
    df = pd.read_csv(CSV_PATH)
    diffs = np.diff(df[df["pass_id"] == 3]["timestamp"].values)
    assert abs(diffs.mean() - SAMPLE_INTERVAL) < INTERVAL_TOLERANCE

def test_sampling_interval_pass_4():
    df = pd.read_csv(CSV_PATH)
    diffs = np.diff(df[df["pass_id"] == 4]["timestamp"].values)
    assert abs(diffs.mean() - SAMPLE_INTERVAL) < INTERVAL_TOLERANCE

def test_no_nan_values_in_sensor_columns():
    df = pd.read_csv(CSV_PATH)
    sensor_cols = ["accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z"]
    assert not df[sensor_cols].isnull().any().any()

def test_gps_coordinates_within_kerala_bounding_box():
    df = pd.read_csv(CSV_PATH)
    assert df["latitude"].between(8.0, 12.8).all()
    assert df["longitude"].between(74.8, 77.5).all()

def test_dataset_sample_count():
    df = pd.read_csv(CSV_PATH)
    assert len(df) > 1000

def test_ground_truth_event_is_binary():
    df = pd.read_csv(CSV_PATH)
    assert set(df["ground_truth_event"].unique()).issubset({0, 1})


# ─── Validation Runner ────────────────────────────────────────────────────────

def run():
    results = []

    print("\n==================================================")
    print("  ROADPULSE -- Sensor Data Validation")
    print("==================================================")

    # 1. File exists
    results.append(_check("CSV file exists", CSV_PATH.exists(), str(CSV_PATH)))
    if not results[-1]:
        print(f"\n[FATAL] File not found at:\n  {CSV_PATH}")
        print("Run  python src/generator/mock_data.py  to generate it.\n")
        sys.exit(1)

    df = pd.read_csv(CSV_PATH)

    # 2. All expected columns present
    missing_cols = set(EXPECTED_COLUMNS) - set(df.columns)
    results.append(_check(
        "All 12 expected columns present",
        len(missing_cols) == 0,
        f"missing: {missing_cols}",
    ))

    # 3. At least MIN_PASSES passes
    n_passes = df["pass_id"].nunique()
    results.append(_check(
        f"At least {MIN_PASSES} passes present",
        n_passes >= MIN_PASSES,
        f"found {n_passes}",
    ))

    # 4. Timestamps monotonically increasing within each pass
    all_ordered = True
    for pid, grp in df.groupby("pass_id"):
        diffs = np.diff(grp["timestamp"].values)
        if not np.all(diffs > 0):
            all_ordered = False
            break
    results.append(_check(
        "Timestamps monotonically increasing within every pass",
        all_ordered,
    ))

    # 5. All required ground_truth_type labels present
    actual_types  = set(df["ground_truth_type"].unique())
    missing_types = EXPECTED_GT_TYPES - actual_types
    results.append(_check(
        "All required ground_truth_type labels present",
        len(missing_types) == 0,
        f"missing: {missing_types}",
    ))

    # 6. Mean sample interval ≈ 0.02 s for each pass
    for pid, grp in df.groupby("pass_id"):
        intervals  = np.diff(grp["timestamp"].values)
        mean_iv    = intervals.mean()
        ok = abs(mean_iv - SAMPLE_INTERVAL) < INTERVAL_TOLERANCE
        results.append(_check(
            f"Pass {pid}: mean sample interval approx {SAMPLE_INTERVAL} s",
            ok,
            f"actual = {mean_iv:.6f} s",
        ))

    # 7. No NaN values in sensor columns
    sensor_cols = ["accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z"]
    has_nan = df[sensor_cols].isnull().any().any()
    results.append(_check("No NaN values in sensor columns", not has_nan))

    # 8. GPS within the Kerala bounding box (rough check)
    #    Kerala: lat 8.0°–12.8° N, lon 74.8°–77.5° E
    lat_ok = df["latitude"].between(8.0, 12.8).all()
    lon_ok = df["longitude"].between(74.8, 77.5).all()
    results.append(_check(
        "GPS coordinates within Kerala bounding box",
        lat_ok and lon_ok,
        f"lat ok={lat_ok}, lon ok={lon_ok}",
    ))

    # 9. More than 1,000 rows
    results.append(_check(
        "Dataset has > 1,000 samples",
        len(df) > 1000,
        f"found {len(df):,}",
    ))

    # 10. ground_truth_event is binary (only 0 or 1)
    event_values = set(df["ground_truth_event"].unique())
    binary_ok    = event_values.issubset({0, 1})
    results.append(_check(
        "ground_truth_event contains only 0 or 1",
        binary_ok,
        f"found values: {event_values}",
    ))

    # ── Summary ───────────────────────────────────────────────────────────────
    n_passed = sum(results)
    n_failed = len(results) - n_passed

    print("==================================================")
    print(f"  Result   : {n_passed} passed,  {n_failed} failed")
    print(f"  Rows     : {len(df):,}")
    print(f"  Passes   : {n_passes}")
    print(f"  CSV size : {CSV_PATH.stat().st_size / 1024:.1f} KB")
    print("==================================================\n")

    if n_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run()
