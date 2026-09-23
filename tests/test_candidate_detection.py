"""
ROADPULSE — Candidate Event Detection Test Suite
================================================
Validates that:
  1. Input features load successfully.
  2. Candidate detector runs and produces output file.
  3. Output row count matches features row count exactly.
  4. Required metadata columns are preserved.
  5. candidate_type contains only valid, expected labels.
  6. candidate flag is binary (0/1) and consistent with candidate_type.
  7. No NaN or infinite values are introduced.
  8. Ground-truth columns are completely absent from detector output.
  9. Detection is fully deterministic across multiple runs.
 10. features.csv is never modified by the detector.
 11. Synthetic feature rows trigger every candidate rule properly (including safe div-by-zero).
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.detect_candidates import (
    INPUT_FEATURES_PATH,
    OUTPUT_CANDIDATES_PATH,
    VALID_CANDIDATE_TYPES,
    REQUIRED_METADATA_COLUMNS,
    load_features,
    classify_window,
    detect_candidates,
    run_pipeline,
)


def _check(label, condition, detail=""):
    icon = "[PASS]" if condition else "[FAIL]"
    line = f"  {icon}  {label}"
    if not condition and detail:
        line += f"  -  {detail}"
    print(line)
    return condition


# ─── Pytest-compatible individual test functions ──────────────────────────────

def test_input_features_load_successfully():
    features_df = load_features(INPUT_FEATURES_PATH)
    assert isinstance(features_df, pd.DataFrame) and len(features_df) > 0


def test_candidate_output_file_created(tmp_path):
    test_out = tmp_path / "test_candidate_events.csv"
    run_pipeline(input_path=INPUT_FEATURES_PATH, output_path=test_out)
    assert test_out.exists()
    assert test_out.stat().st_size > 0


def test_output_row_count_matches_features():
    features_df = load_features(INPUT_FEATURES_PATH)
    candidates_df = detect_candidates(features_df)
    assert len(candidates_df) == len(features_df)


def test_required_metadata_columns_preserved():
    features_df = load_features(INPUT_FEATURES_PATH)
    candidates_df = detect_candidates(features_df)
    for col in REQUIRED_METADATA_COLUMNS:
        assert col in candidates_df.columns, f"Missing metadata column: {col}"


def test_candidate_type_valid_labels():
    features_df = load_features(INPUT_FEATURES_PATH)
    candidates_df = detect_candidates(features_df)
    unique_labels = set(candidates_df["candidate_type"].unique())
    invalid = unique_labels - VALID_CANDIDATE_TYPES
    assert len(invalid) == 0, f"Unexpected candidate types found: {invalid}"


def test_candidate_flag_is_binary_and_consistent():
    features_df = load_features(INPUT_FEATURES_PATH)
    candidates_df = detect_candidates(features_df)
    unique_flags = set(candidates_df["candidate"].unique())
    assert unique_flags.issubset({0, 1}), f"Non-binary flags found: {unique_flags}"

    # Consistency check: candidate == 0 iff candidate_type == 'normal'
    normal_flags = candidates_df[candidates_df["candidate_type"] == "normal"]["candidate"]
    assert (normal_flags == 0).all(), "Found candidate != 0 for normal type"

    non_normal_flags = candidates_df[candidates_df["candidate_type"] != "normal"]["candidate"]
    assert (non_normal_flags == 1).all(), "Found candidate != 1 for non-normal type"


def test_no_nan_or_infinite_values_introduced():
    features_df = load_features(INPUT_FEATURES_PATH)
    candidates_df = detect_candidates(features_df)
    assert not candidates_df["candidate_type"].isna().any(), "NaN found in candidate_type"
    assert not candidates_df["candidate"].isna().any(), "NaN found in candidate flag"


def test_ground_truth_columns_not_present():
    features_df = load_features(INPUT_FEATURES_PATH)
    candidates_df = detect_candidates(features_df)
    forbidden = ["ground_truth_event", "ground_truth_type"]
    found = [c for c in forbidden if c in candidates_df.columns]
    assert len(found) == 0, f"Ground-truth columns found in output: {found}"


def test_detection_is_deterministic():
    features_df = load_features(INPUT_FEATURES_PATH)
    run_1 = detect_candidates(features_df)
    run_2 = detect_candidates(features_df)
    assert run_1["candidate_type"].equals(run_2["candidate_type"])
    assert run_1["candidate"].equals(run_2["candidate"])


def test_features_csv_remains_unmodified():
    mtime_before = INPUT_FEATURES_PATH.stat().st_mtime
    size_before = INPUT_FEATURES_PATH.stat().st_size

    features_df = load_features(INPUT_FEATURES_PATH)
    _ = detect_candidates(features_df)

    mtime_after = INPUT_FEATURES_PATH.stat().st_mtime
    size_after = INPUT_FEATURES_PATH.stat().st_size
    assert mtime_before == mtime_after and size_before == size_after


def test_synthetic_rules_trigger_all_candidate_types():
    """Verify each hierarchical rule independently triggers its target label."""
    # Baseline template with neutral non-event values
    baseline = {
        "gyro_z_max_abs": 0.003,
        "accel_x_max_abs": 0.04,
        "accel_y_mean": 0.0,
        "accel_z_peak_to_peak": 0.17,
        "accel_z_max_abs_diff": 0.07,
        "accel_z_std": 0.04,
    }

    # 1. Normal
    assert classify_window(pd.Series(baseline)) == "normal"

    # 2. Turning
    row = dict(baseline, gyro_z_max_abs=0.030, accel_x_max_abs=0.35)
    assert classify_window(pd.Series(row)) == "turning_candidate"

    # 3. Braking
    row = dict(baseline, accel_y_mean=-0.60)
    assert classify_window(pd.Series(row)) == "braking_candidate"

    # 4. Acceleration
    row = dict(baseline, accel_y_mean=0.30)
    assert classify_window(pd.Series(row)) == "acceleration_candidate"

    # 5. Speed Breaker
    row = dict(baseline, accel_z_peak_to_peak=1.80)
    assert classify_window(pd.Series(row)) == "speed_breaker_candidate"

    # 6. Pothole (ratio = 1.0 / 0.20 = 5.0 > 4.0)
    row = dict(baseline, accel_z_max_abs_diff=0.25, accel_z_peak_to_peak=1.0, accel_z_std=0.20)
    assert classify_window(pd.Series(row)) == "pothole_candidate"

    # 7. Rough Road
    row = dict(baseline, accel_z_std=0.20, accel_z_peak_to_peak=0.80)
    assert classify_window(pd.Series(row)) == "rough_road_candidate"

    # Safe division test: zero or negative std
    row_zero_std = dict(baseline, accel_z_std=0.0, accel_z_max_abs_diff=0.25, accel_z_peak_to_peak=1.0)
    # Should not crash with ZeroDivisionError
    result = classify_window(pd.Series(row_zero_std))
    assert result in VALID_CANDIDATE_TYPES


def run():
    """CLI runner."""
    results = []

    print("\n==================================================")
    print("  ROADPULSE -- Candidate Detection Validation")
    print("==================================================")

    features_df = load_features(INPUT_FEATURES_PATH)
    results.append(_check("Input features load successfully", len(features_df) > 0))

    candidates_df = detect_candidates(features_df)
    results.append(_check("Output row count matches input features", len(candidates_df) == len(features_df)))

    meta_ok = all(c in candidates_df.columns for c in REQUIRED_METADATA_COLUMNS)
    results.append(_check("Required metadata columns preserved", meta_ok))

    labels_ok = set(candidates_df["candidate_type"].unique()).issubset(VALID_CANDIDATE_TYPES)
    results.append(_check("candidate_type contains only valid labels", labels_ok))

    flags_ok = set(candidates_df["candidate"].unique()).issubset({0, 1})
    consistent = (
        (candidates_df[candidates_df["candidate_type"] == "normal"]["candidate"] == 0).all() and
        (candidates_df[candidates_df["candidate_type"] != "normal"]["candidate"] == 1).all()
    )
    results.append(_check("candidate flag is binary and consistent", flags_ok and consistent))

    no_nans = not candidates_df[["candidate_type", "candidate"]].isna().any().any()
    results.append(_check("No NaN or infinite values introduced", no_nans))

    no_gt = not any(c in candidates_df.columns for c in ["ground_truth_event", "ground_truth_type"])
    results.append(_check("Ground-truth columns completely absent", no_gt))

    # Synthetic rule checks
    try:
        test_synthetic_rules_trigger_all_candidate_types()
        synth_ok = True
    except AssertionError:
        synth_ok = False
    results.append(_check("Synthetic rules trigger all candidate types cleanly", synth_ok))

    n_passed = sum(results)
    n_failed = len(results) - n_passed

    print("==================================================")
    print(f"  Result   : {n_passed} passed,  {n_failed} failed")
    print(f"  Windows  : {len(candidates_df):,}")
    print("==================================================\n")

    if n_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run()
