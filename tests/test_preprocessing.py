"""
ROADPULSE — Preprocessing Validation Test Suite
================================================
Validates that:
  1. Raw sensor data loads properly.
  2. All original raw columns are preserved intact.
  3. All expected processed signal columns are created.
  4. No unexpected NaN values are introduced anywhere.
  5. Total row count matches the raw dataset exactly (12,200 rows).
  6. All four passes remain present.
  7. Timestamps and ordering are preserved within each pass.
  8. Preprocessing pipeline does not mutate or overwrite the raw CSV.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.preprocessing import (
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    load_sensor_data,
    preprocess_dataset,
    save_preprocessed_data,
)

EXPECTED_RAW_COLUMNS = [
    "timestamp", "pass_id", "latitude", "longitude",
    "accel_x", "accel_y", "accel_z",
    "gyro_x", "gyro_y", "gyro_z",
    "ground_truth_event", "ground_truth_type",
]

EXPECTED_PROCESSED_COLUMNS = [
    "accel_x_smooth",
    "accel_y_smooth",
    "accel_z_smooth",
    "accel_z_baseline",
    "accel_z_dynamic",
    "gyro_x_smooth",
    "gyro_y_smooth",
    "gyro_z_smooth",
]

def _check(label, condition, detail=""):
    icon = "[PASS]" if condition else "[FAIL]"
    line = f"  {icon}  {label}"
    if not condition and detail:
        line += f"  -  {detail}"
    print(line)
    return condition


# ─── Pytest-compatible individual test functions ──────────────────────────────

def _load_data():
    """Helper: load raw data and run preprocessing in-memory."""
    raw_df = load_sensor_data(RAW_DATA_PATH)
    processed_df = preprocess_dataset(raw_df)
    return raw_df, processed_df


def test_raw_dataset_loads_successfully():
    raw_df = load_sensor_data(RAW_DATA_PATH)
    assert isinstance(raw_df, pd.DataFrame) and len(raw_df) > 0


def test_all_expected_raw_columns_remain():
    raw_df, processed_df = _load_data()
    assert all(col in processed_df.columns for col in EXPECTED_RAW_COLUMNS)


def test_all_expected_processed_columns_exist():
    raw_df, processed_df = _load_data()
    missing = set(EXPECTED_PROCESSED_COLUMNS) - set(processed_df.columns)
    assert len(missing) == 0, f"missing: {missing}"


def test_no_nan_values_introduced():
    raw_df, processed_df = _load_data()
    nan_cols = processed_df.columns[processed_df.isna().any()].tolist()
    assert not processed_df.isna().any().any(), f"columns with NaN: {nan_cols}"


def test_row_count_unchanged():
    raw_df, processed_df = _load_data()
    assert len(processed_df) == len(raw_df), (
        f"raw: {len(raw_df)}, processed: {len(processed_df)}"
    )


def test_all_four_passes_remain():
    raw_df, processed_df = _load_data()
    raw_passes = set(raw_df["pass_id"].unique())
    proc_passes = set(processed_df["pass_id"].unique())
    assert raw_passes == proc_passes and len(proc_passes) == 4, (
        f"passes found: {proc_passes}"
    )


def test_timestamps_and_raw_signals_unchanged():
    raw_df, processed_df = _load_data()
    assert np.allclose(processed_df["timestamp"], raw_df["timestamp"])
    assert np.allclose(processed_df["accel_z"], raw_df["accel_z"])


def test_dynamic_vertical_acceleration_centered_near_zero():
    raw_df, processed_df = _load_data()
    normal_driving = processed_df[processed_df["ground_truth_type"] == "none"]
    mean_dyn = abs(float(normal_driving["accel_z_dynamic"].mean()))
    assert mean_dyn < 0.10, f"mean dynamic accel_z: {mean_dyn:.4f} m/s^2"


def test_raw_csv_not_modified():
    mtime_before = RAW_DATA_PATH.stat().st_mtime
    size_before = RAW_DATA_PATH.stat().st_size
    _load_data()
    mtime_after = RAW_DATA_PATH.stat().st_mtime
    size_after = RAW_DATA_PATH.stat().st_size
    assert mtime_before == mtime_after and size_before == size_after


def run():
    results = []

    print("\n==================================================")
    print("  ROADPULSE -- Preprocessing Validation")
    print("==================================================")

    # 1. Load raw data and record its fingerprint/mtime
    raw_mtime_before = RAW_DATA_PATH.stat().st_mtime
    raw_size_before = RAW_DATA_PATH.stat().st_size

    try:
        raw_df = load_sensor_data(RAW_DATA_PATH)
        can_load = isinstance(raw_df, pd.DataFrame) and len(raw_df) > 0
    except Exception as e:
        can_load = False

    results.append(_check("Raw dataset loads successfully", can_load))
    if not can_load:
        print("\n[FATAL] Unable to load raw dataset. Exiting test.")
        sys.exit(1)

    # Run preprocessing in-memory
    processed_df = preprocess_dataset(raw_df)

    # 2. Expected raw columns remain
    raw_cols_preserved = all(col in processed_df.columns for col in EXPECTED_RAW_COLUMNS)
    results.append(_check("All expected raw columns remain", raw_cols_preserved))

    # 3. Expected processed columns exist
    proc_cols_exist = all(col in processed_df.columns for col in EXPECTED_PROCESSED_COLUMNS)
    results.append(_check(
        "All expected processed columns exist",
        proc_cols_exist,
        f"missing: {set(EXPECTED_PROCESSED_COLUMNS) - set(processed_df.columns)}",
    ))

    # 4. No unexpected NaN values
    has_nans = processed_df.isna().any().any()
    nan_cols = processed_df.columns[processed_df.isna().any()].tolist()
    results.append(_check(
        "No unexpected NaN values introduced",
        not has_nans,
        f"columns with NaN: {nan_cols}",
    ))

    # 5. Row count unchanged
    row_count_ok = len(processed_df) == len(raw_df)
    results.append(_check(
        f"Row count unchanged ({len(raw_df):,} rows)",
        row_count_ok,
        f"raw: {len(raw_df)}, processed: {len(processed_df)}",
    ))

    # 6. All four passes remain present
    raw_passes = set(raw_df["pass_id"].unique())
    proc_passes = set(processed_df["pass_id"].unique())
    passes_ok = raw_passes == proc_passes and len(proc_passes) == 4
    results.append(_check(
        "All four passes remain present",
        passes_ok,
        f"passes found: {proc_passes}",
    ))

    # 7. Timestamps and raw sensor values identical
    timestamps_match = np.allclose(processed_df["timestamp"], raw_df["timestamp"])
    accel_raw_match = np.allclose(processed_df["accel_z"], raw_df["accel_z"])
    results.append(_check(
        "Timestamps and raw signals remain unchanged",
        timestamps_match and accel_raw_match,
    ))

    # 8. Dynamic vertical acceleration centered near 0 on smooth sections
    normal_driving = processed_df[processed_df["ground_truth_type"] == "none"]
    mean_dyn = abs(float(normal_driving["accel_z_dynamic"].mean()))
    results.append(_check(
        "Dynamic vertical acceleration centers near 0 on flat road",
        mean_dyn < 0.10,
        f"mean dynamic accel_z: {mean_dyn:.4f} m/s^2",
    ))

    # 9. Verify raw CSV was not modified
    raw_mtime_after = RAW_DATA_PATH.stat().st_mtime
    raw_size_after = RAW_DATA_PATH.stat().st_size
    raw_unmodified = (raw_mtime_before == raw_mtime_after) and (raw_size_before == raw_size_after)
    results.append(_check("Raw CSV was not modified", raw_unmodified))

    # Summary
    n_passed = sum(results)
    n_failed = len(results) - n_passed

    print("==================================================")
    print(f"  Result   : {n_passed} passed,  {n_failed} failed")
    print(f"  Columns  : {len(processed_df.columns)} total")
    print("==================================================\n")

    if n_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run()
