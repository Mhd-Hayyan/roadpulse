"""
ROADPULSE — Temporal / Context Event Filtering Test Suite (Milestone 8)
======================================================================
Validates that:
  1. Input classified events load successfully.
  2. Filtered events output file is created.
  3. Vehicle dynamics and normal driving windows are completely excluded.
  4. Overlapping same-type windows merge into single physical events.
  5. Adjacent same-type windows (within 0.30s) merge.
  6. Potholes remain separate from sustained rough-road sections.
  7. Speed-breaker boundary roughness is absorbed into speed-breaker events.
  8. Sustained rough-road sections are preserved as separate events.
  9. GPS center coordinates are valid, finite, and within Kerala bounds.
 10. Event IDs are unique across all passes.
 11. Filtering pipeline is deterministic across runs.
 12. Ground truth is not used or present in output.
 13. All required output columns are present with valid types.
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.filter_events import (
    INPUT_CLASSIFIED_PATH,
    OUTPUT_FILTERED_PATH,
    ROAD_EVENT_TYPES,
    REQUIRED_OUTPUT_COLUMNS,
    load_classified_events,
    filter_road_events,
    cluster_same_type_windows,
    absorb_speed_breaker_boundaries,
    filter_and_consolidate_events,
    run_pipeline,
)

# Kerala geographic bounding box
KERALA_LAT_MIN = 8.0
KERALA_LAT_MAX = 13.0
KERALA_LON_MIN = 74.5
KERALA_LON_MAX = 77.5


def _check(label, condition, detail=""):
    icon = "[PASS]" if condition else "[FAIL]"
    line = f"  {icon}  {label}"
    if not condition and detail:
        line += f"  -  {detail}"
    print(line)
    return condition


# ─── Pytest-compatible individual test functions ──────────────────────────────

def test_input_classified_events_load():
    df = load_classified_events(INPUT_CLASSIFIED_PATH)
    assert isinstance(df, pd.DataFrame) and len(df) > 0


def test_filtered_output_file_created(tmp_path):
    test_out = tmp_path / "test_filtered_events.csv"
    run_pipeline(input_path=INPUT_CLASSIFIED_PATH, output_path=test_out)
    assert test_out.exists()
    assert test_out.stat().st_size > 0


def test_vehicle_dynamics_excluded():
    classified_df = load_classified_events(INPUT_CLASSIFIED_PATH)
    filtered_df = filter_and_consolidate_events(classified_df)

    forbidden_types = {"normal", "turning", "braking", "acceleration"}
    found_forbidden = set(filtered_df["event_type"].unique()).intersection(forbidden_types)
    assert len(found_forbidden) == 0, f"Found non-road event types in filtered output: {found_forbidden}"
    assert set(filtered_df["event_type"].unique()).issubset(ROAD_EVENT_TYPES)


def test_required_output_columns_present():
    classified_df = load_classified_events(INPUT_CLASSIFIED_PATH)
    filtered_df = filter_and_consolidate_events(classified_df)

    for col in REQUIRED_OUTPUT_COLUMNS:
        assert col in filtered_df.columns, f"Missing required column: {col}"
    assert list(filtered_df.columns) == REQUIRED_OUTPUT_COLUMNS


def test_overlapping_same_type_windows_merge():
    """Synthetic test: 3 overlapping pothole windows should merge into 1 event."""
    synth_windows = pd.DataFrame([
        {
            "pass_id": 1,
            "window_start": 10.0,
            "window_end": 10.48,
            "event_type": "pothole",
            "is_road_event": 1,
            "gps_lat_start": 9.9320,
            "gps_lon_start": 76.2680,
            "gps_lat_end": 9.9321,
            "gps_lon_end": 76.2681,
        },
        {
            "pass_id": 1,
            "window_start": 10.24,
            "window_end": 10.72,
            "event_type": "pothole",
            "is_road_event": 1,
            "gps_lat_start": 9.9321,
            "gps_lon_start": 76.2681,
            "gps_lat_end": 9.9322,
            "gps_lon_end": 76.2682,
        },
        {
            "pass_id": 1,
            "window_start": 10.48,
            "window_end": 10.96,
            "event_type": "pothole",
            "is_road_event": 1,
            "gps_lat_start": 9.9322,
            "gps_lon_start": 76.2682,
            "gps_lat_end": 9.9323,
            "gps_lon_end": 76.2683,
        },
    ])
    consolidated = filter_and_consolidate_events(synth_windows)
    assert len(consolidated) == 1
    assert consolidated.iloc[0]["event_type"] == "pothole"
    assert consolidated.iloc[0]["window_count"] == 3
    assert consolidated.iloc[0]["start_time"] == 10.0
    assert consolidated.iloc[0]["end_time"] == 10.96


def test_adjacent_same_type_windows_merge():
    """Synthetic test: 2 adjacent windows separated by 0.20s (< 0.30s) should merge."""
    synth_windows = pd.DataFrame([
        {
            "pass_id": 1,
            "window_start": 5.0,
            "window_end": 5.48,
            "event_type": "rough_road",
            "is_road_event": 1,
            "gps_lat_start": 9.9320,
            "gps_lon_start": 76.2680,
            "gps_lat_end": 9.9321,
            "gps_lon_end": 76.2681,
        },
        {
            "pass_id": 1,
            "window_start": 5.68,
            "window_end": 6.16,
            "event_type": "rough_road",
            "is_road_event": 1,
            "gps_lat_start": 9.9322,
            "gps_lon_start": 76.2682,
            "gps_lat_end": 9.9323,
            "gps_lon_end": 76.2683,
        },
    ])
    consolidated = filter_and_consolidate_events(synth_windows)
    assert len(consolidated) == 1
    assert consolidated.iloc[0]["event_type"] == "rough_road"
    assert consolidated.iloc[0]["window_count"] == 2
    assert consolidated.iloc[0]["start_time"] == 5.0
    assert consolidated.iloc[0]["end_time"] == 6.16


def test_pothole_separate_from_sustained_rough_road():
    """Verify that potholes adjacent to rough road sections are NOT absorbed into rough road."""
    classified_df = load_classified_events(INPUT_CLASSIFIED_PATH)
    filtered_df = filter_and_consolidate_events(classified_df)

    # In Pass 1, window 98 is a pothole at 23.52s, followed immediately by rough road at 23.76s
    p1_events = filtered_df[filtered_df["pass_id"] == 1].sort_values("start_time")
    p1_types = list(p1_events["event_type"])

    # Ensure both pothole and rough_road exist as separate distinct events
    assert "pothole" in p1_types
    assert "rough_road" in p1_types
    assert len(p1_events) >= 3


def test_speed_breaker_absorbs_boundary_roughness():
    """Verify speed-breaker absorbs boundary rough_road in the actual dataset."""
    classified_df = load_classified_events(INPUT_CLASSIFIED_PATH)
    filtered_df = filter_and_consolidate_events(classified_df)

    for pid in filtered_df["pass_id"].unique():
        p_events = filtered_df[filtered_df["pass_id"] == pid]
        sb_events = p_events[p_events["event_type"] == "speed_breaker"]
        assert len(sb_events) == 1, f"Expected exactly 1 speed breaker in pass {pid}, got {len(sb_events)}"
        # The speed breaker absorbed boundary windows, so window_count should be >= 6
        assert sb_events.iloc[0]["window_count"] >= 6


def test_sustained_rough_road_preserved():
    """Verify sustained rough road sections are preserved as independent events in all passes."""
    classified_df = load_classified_events(INPUT_CLASSIFIED_PATH)
    filtered_df = filter_and_consolidate_events(classified_df)

    for pid in filtered_df["pass_id"].unique():
        p_events = filtered_df[filtered_df["pass_id"] == pid]
        rr_events = p_events[p_events["event_type"] == "rough_road"]
        assert len(rr_events) == 1, f"Expected exactly 1 sustained rough road in pass {pid}, got {len(rr_events)}"
        # Sustained rough road section has ~28-30 windows and duration > 6.0s
        assert rr_events.iloc[0]["window_count"] >= 20
        assert rr_events.iloc[0]["duration"] >= 6.0


def test_gps_coordinates_valid():
    classified_df = load_classified_events(INPUT_CLASSIFIED_PATH)
    filtered_df = filter_and_consolidate_events(classified_df)

    assert not filtered_df["center_latitude"].isna().any()
    assert not filtered_df["center_longitude"].isna().any()
    assert np.all(np.isfinite(filtered_df["center_latitude"]))
    assert np.all(np.isfinite(filtered_df["center_longitude"]))

    assert (filtered_df["center_latitude"] >= KERALA_LAT_MIN).all()
    assert (filtered_df["center_latitude"] <= KERALA_LAT_MAX).all()
    assert (filtered_df["center_longitude"] >= KERALA_LON_MIN).all()
    assert (filtered_df["center_longitude"] <= KERALA_LON_MAX).all()


def test_event_ids_unique():
    classified_df = load_classified_events(INPUT_CLASSIFIED_PATH)
    filtered_df = filter_and_consolidate_events(classified_df)
    assert filtered_df["event_id"].nunique() == len(filtered_df)


def test_output_is_deterministic():
    classified_df = load_classified_events(INPUT_CLASSIFIED_PATH)
    run_1 = filter_and_consolidate_events(classified_df)
    run_2 = filter_and_consolidate_events(classified_df)
    assert run_1.equals(run_2)


def test_ground_truth_not_present():
    classified_df = load_classified_events(INPUT_CLASSIFIED_PATH)
    filtered_df = filter_and_consolidate_events(classified_df)

    forbidden = ["ground_truth_event", "ground_truth_type"]
    found = [c for c in forbidden if c in filtered_df.columns]
    assert len(found) == 0, f"Ground-truth columns found in filtered output: {found}"


def run():
    """CLI runner."""
    results = []

    print("\n==================================================")
    print("  ROADPULSE -- Event Filtering Validation (Milestone 8)")
    print("==================================================")

    classified_df = load_classified_events(INPUT_CLASSIFIED_PATH)
    results.append(_check("Input classified events load successfully", len(classified_df) > 0))

    filtered_df = filter_and_consolidate_events(classified_df)
    results.append(_check("Physical events produced", len(filtered_df) > 0))

    no_dynamics = not any(t in filtered_df["event_type"].values for t in ["normal", "turning", "braking", "acceleration"])
    results.append(_check("Vehicle dynamics excluded from output", no_dynamics))

    cols_ok = list(filtered_df.columns) == REQUIRED_OUTPUT_COLUMNS
    results.append(_check("All required output columns present", cols_ok))

    ids_unique = filtered_df["event_id"].nunique() == len(filtered_df)
    results.append(_check("Event IDs are unique", ids_unique))

    gps_ok = (
        (filtered_df["center_latitude"] >= KERALA_LAT_MIN).all() and
        (filtered_df["center_latitude"] <= KERALA_LAT_MAX).all() and
        (filtered_df["center_longitude"] >= KERALA_LON_MIN).all() and
        (filtered_df["center_longitude"] <= KERALA_LON_MAX).all()
    )
    results.append(_check("GPS center coordinates within Kerala bounds", gps_ok))

    # Context absorption checks
    sb_count = (filtered_df["event_type"] == "speed_breaker").sum()
    rr_count = (filtered_df["event_type"] == "rough_road").sum()
    ph_count = (filtered_df["event_type"] == "pothole").sum()
    results.append(_check("Speed breaker boundary roughness absorbed (exactly 4 speed breakers)", sb_count == 4))
    results.append(_check("Sustained rough road sections preserved (exactly 4 rough road sections)", rr_count == 4))
    results.append(_check("Pothole events detected and separate", ph_count >= 4))

    no_gt = not any(c in filtered_df.columns for c in ["ground_truth_event", "ground_truth_type"])
    results.append(_check("Ground-truth columns completely absent", no_gt))

    n_passed = sum(results)
    n_failed = len(results) - n_passed

    print("==================================================")
    print(f"  Result   : {n_passed} passed,  {n_failed} failed")
    print(f"  Events   : {len(filtered_df)}")
    print("==================================================\n")

    if n_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run()
