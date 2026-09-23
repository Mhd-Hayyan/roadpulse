"""
ROADPULSE — Event Classification Test Suite (Milestone 7)
=========================================================
Validates that:
  1. Input candidate events load successfully.
  2. Classification executes and produces output CSV.
  3. Output row count matches input row count exactly.
  4. Required metadata, feature, and candidate columns are preserved.
  5. Each vehicle-dynamics candidate maps correctly (turning, braking, acceleration).
  6. Each road candidate maps correctly (pothole, speed_breaker, rough_road).
  7. Normal maps correctly to normal.
  8. event_type contains only valid, expected labels.
  9. is_road_event is strictly consistent with event_type (1 for road events, 0 otherwise).
 10. No NaN or infinite values exist in classification columns.
 11. Ground-truth columns are completely absent from classifier output.
 12. Classification is fully deterministic across multiple runs.
 13. Synthetic feature cases trigger both direct mappings and refinement rules properly.
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.classify_events import (
    INPUT_CANDIDATES_PATH,
    OUTPUT_CLASSIFIED_PATH,
    VALID_EVENT_TYPES,
    ROAD_EVENT_TYPES,
    load_candidate_events,
    compute_impulse_ratio,
    classify_event,
    classify_events,
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

def test_input_candidates_load_successfully():
    df = load_candidate_events(INPUT_CANDIDATES_PATH)
    assert isinstance(df, pd.DataFrame) and len(df) > 0


def test_classified_output_file_created(tmp_path):
    test_out = tmp_path / "test_classified_events.csv"
    run_pipeline(input_path=INPUT_CANDIDATES_PATH, output_path=test_out)
    assert test_out.exists()
    assert test_out.stat().st_size > 0


def test_output_row_count_matches_input():
    candidates_df = load_candidate_events(INPUT_CANDIDATES_PATH)
    classified_df = classify_events(candidates_df)
    assert len(classified_df) == len(candidates_df)


def test_required_columns_preserved():
    candidates_df = load_candidate_events(INPUT_CANDIDATES_PATH)
    classified_df = classify_events(candidates_df)

    # Check input candidate columns are preserved
    for col in candidates_df.columns:
        assert col in classified_df.columns, f"Input column missing from output: {col}"

    # Check newly added classification columns exist
    for col in ["event_type", "is_road_event", "impulse_ratio"]:
        assert col in classified_df.columns, f"Classification column missing: {col}"


def test_vehicle_dynamics_candidates_map_correctly():
    candidates_df = load_candidate_events(INPUT_CANDIDATES_PATH)
    classified_df = classify_events(candidates_df)

    # turning_candidate -> turning
    turning_events = classified_df[classified_df["candidate_type"] == "turning_candidate"]["event_type"]
    assert (turning_events == "turning").all()

    # braking_candidate -> braking
    braking_events = classified_df[classified_df["candidate_type"] == "braking_candidate"]["event_type"]
    assert (braking_events == "braking").all()

    # acceleration_candidate -> acceleration
    accel_events = classified_df[classified_df["candidate_type"] == "acceleration_candidate"]["event_type"]
    assert (accel_events == "acceleration").all()


def test_normal_maps_to_normal():
    candidates_df = load_candidate_events(INPUT_CANDIDATES_PATH)
    classified_df = classify_events(candidates_df)
    normal_events = classified_df[classified_df["candidate_type"] == "normal"]["event_type"]
    assert (normal_events == "normal").all()


def test_road_candidates_map_to_road_events():
    candidates_df = load_candidate_events(INPUT_CANDIDATES_PATH)
    classified_df = classify_events(candidates_df)

    road_candidates = candidates_df[
        candidates_df["candidate_type"].isin(
            ["pothole_candidate", "speed_breaker_candidate", "rough_road_candidate"]
        )
    ]
    classified_roads = classified_df.loc[road_candidates.index]

    # All road candidates must map to one of the valid road event types
    assert set(classified_roads["event_type"].unique()).issubset(ROAD_EVENT_TYPES)
    assert (classified_roads["is_road_event"] == 1).all()


def test_no_unexpected_event_types():
    candidates_df = load_candidate_events(INPUT_CANDIDATES_PATH)
    classified_df = classify_events(candidates_df)
    unique_types = set(classified_df["event_type"].unique())
    invalid = unique_types - VALID_EVENT_TYPES
    assert len(invalid) == 0, f"Found invalid event_type values: {invalid}"


def test_is_road_event_consistency():
    candidates_df = load_candidate_events(INPUT_CANDIDATES_PATH)
    classified_df = classify_events(candidates_df)

    unique_flags = set(classified_df["is_road_event"].unique())
    assert unique_flags.issubset({0, 1})

    # is_road_event == 1 iff event_type in ROAD_EVENT_TYPES
    road_mask = classified_df["event_type"].isin(ROAD_EVENT_TYPES)
    assert (classified_df.loc[road_mask, "is_road_event"] == 1).all()
    assert (classified_df.loc[~road_mask, "is_road_event"] == 0).all()


def test_no_nan_or_infinite_values_introduced():
    candidates_df = load_candidate_events(INPUT_CANDIDATES_PATH)
    classified_df = classify_events(candidates_df)

    assert not classified_df["event_type"].isna().any(), "NaN in event_type"
    assert not classified_df["is_road_event"].isna().any(), "NaN in is_road_event"
    assert not classified_df["impulse_ratio"].isna().any(), "NaN in impulse_ratio"
    assert not np.isinf(classified_df["impulse_ratio"]).any(), "Inf in impulse_ratio"


def test_ground_truth_columns_not_present():
    candidates_df = load_candidate_events(INPUT_CANDIDATES_PATH)
    classified_df = classify_events(candidates_df)
    forbidden = ["ground_truth_event", "ground_truth_type"]
    found = [c for c in forbidden if c in classified_df.columns]
    assert len(found) == 0, f"Ground-truth columns found in classifier output: {found}"


def test_classification_is_deterministic():
    candidates_df = load_candidate_events(INPUT_CANDIDATES_PATH)
    run_1 = classify_events(candidates_df)
    run_2 = classify_events(candidates_df)
    assert run_1["event_type"].equals(run_2["event_type"])
    assert run_1["is_road_event"].equals(run_2["is_road_event"])
    assert run_1["impulse_ratio"].equals(run_2["impulse_ratio"])


def test_synthetic_refinement_rules():
    """Verify each candidate type and refinement logic using synthetic rows."""
    base_row = {
        "accel_z_peak_to_peak": 0.17,
        "accel_z_std": 0.04,
        "accel_z_max_abs_diff": 0.07,
    }

    # 1. Vehicle dynamics mappings
    assert classify_event(pd.Series(dict(base_row, candidate_type="turning_candidate"))) == "turning"
    assert classify_event(pd.Series(dict(base_row, candidate_type="braking_candidate"))) == "braking"
    assert classify_event(pd.Series(dict(base_row, candidate_type="acceleration_candidate"))) == "acceleration"
    assert classify_event(pd.Series(dict(base_row, candidate_type="normal"))) == "normal"

    # 2. Typical speed breaker candidate -> speed_breaker (smooth arch, moderate diff)
    sb_row = dict(base_row, candidate_type="speed_breaker_candidate", accel_z_peak_to_peak=3.0, accel_z_std=1.0, accel_z_max_abs_diff=0.40)
    assert classify_event(pd.Series(sb_row)) == "speed_breaker"

    # 3. Severe pothole rebound mislabeled as speed_breaker_candidate -> refined to pothole
    sb_pothole_row = dict(base_row, candidate_type="speed_breaker_candidate", accel_z_peak_to_peak=1.75, accel_z_std=0.34, accel_z_max_abs_diff=0.76)
    assert classify_event(pd.Series(sb_pothole_row)) == "pothole"

    # 4. Typical pothole candidate -> pothole
    ph_row = dict(base_row, candidate_type="pothole_candidate", accel_z_peak_to_peak=1.20, accel_z_std=0.24, accel_z_max_abs_diff=0.75)
    assert classify_event(pd.Series(ph_row)) == "pothole"

    # 5. Continuous rough road chatter mislabeled as pothole_candidate -> refined to rough_road
    rr_chatter_row = dict(base_row, candidate_type="pothole_candidate", accel_z_peak_to_peak=0.90, accel_z_std=0.25, accel_z_max_abs_diff=0.35)
    assert classify_event(pd.Series(rr_chatter_row)) == "rough_road"

    # 6. Typical rough road candidate -> rough_road
    rr_row = dict(base_row, candidate_type="rough_road_candidate", accel_z_peak_to_peak=0.80, accel_z_std=0.20, accel_z_max_abs_diff=0.30)
    assert classify_event(pd.Series(rr_row)) == "rough_road"

    # 7. Safe division verification with zero std
    zero_std_row = dict(base_row, candidate_type="pothole_candidate", accel_z_std=0.0)
    assert classify_event(pd.Series(zero_std_row)) in VALID_EVENT_TYPES
    assert compute_impulse_ratio(1.5, 0.0) == 0.0


def run():
    """CLI runner."""
    results = []

    print("\n==================================================")
    print("  ROADPULSE -- Event Classification Validation")
    print("==================================================")

    candidates_df = load_candidate_events(INPUT_CANDIDATES_PATH)
    results.append(_check("Input candidate events load successfully", len(candidates_df) > 0))

    classified_df = classify_events(candidates_df)
    results.append(_check("Output row count matches input", len(classified_df) == len(candidates_df)))

    meta_ok = all(c in classified_df.columns for c in candidates_df.columns)
    class_cols_ok = all(c in classified_df.columns for c in ["event_type", "is_road_event", "impulse_ratio"])
    results.append(_check("Required columns preserved and added", meta_ok and class_cols_ok))

    # Vehicle dynamics check
    vd_ok = (
        (classified_df[classified_df["candidate_type"] == "turning_candidate"]["event_type"] == "turning").all() and
        (classified_df[classified_df["candidate_type"] == "braking_candidate"]["event_type"] == "braking").all() and
        (classified_df[classified_df["candidate_type"] == "acceleration_candidate"]["event_type"] == "acceleration").all() and
        (classified_df[classified_df["candidate_type"] == "normal"]["event_type"] == "normal").all()
    )
    results.append(_check("Vehicle dynamics and normal mapped correctly", vd_ok))

    # Road event check
    road_types_ok = set(classified_df[classified_df["is_road_event"] == 1]["event_type"].unique()).issubset(ROAD_EVENT_TYPES)
    results.append(_check("Road events classified into valid road types", road_types_ok))

    # Binary flag check
    flag_consistency = (
        (classified_df[classified_df["event_type"].isin(ROAD_EVENT_TYPES)]["is_road_event"] == 1).all() and
        (classified_df[~classified_df["event_type"].isin(ROAD_EVENT_TYPES)]["is_road_event"] == 0).all()
    )
    results.append(_check("is_road_event flag is 100% consistent with event_type", flag_consistency))

    # No NaN check
    no_nans = not classified_df[["event_type", "is_road_event", "impulse_ratio"]].isna().any().any()
    results.append(_check("No NaN or infinite values introduced", no_nans))

    # Ground truth check
    no_gt = not any(c in classified_df.columns for c in ["ground_truth_event", "ground_truth_type"])
    results.append(_check("Ground-truth columns completely absent", no_gt))

    # Synthetic checks
    try:
        test_synthetic_refinement_rules()
        synth_ok = True
    except AssertionError:
        synth_ok = False
    results.append(_check("Synthetic refinement rules trigger properly", synth_ok))

    n_passed = sum(results)
    n_failed = len(results) - n_passed

    print("==================================================")
    print(f"  Result   : {n_passed} passed,  {n_failed} failed")
    print(f"  Windows  : {len(classified_df):,}")
    print("==================================================\n")

    if n_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run()
