"""
Tests for M9B: Offline Map Matching
=====================================
Every test_* function is collected by pytest automatically.
The run() function at the bottom is a standalone CLI checker.
"""

import os
import math
import pytest
import pandas as pd
import numpy as np

from src.geospatial.map_matching import (
    ROUTE_SEGMENTS,
    haversine_distance,
    point_to_segment_distance,
    match_event_to_segment,
    process_map_matching,
    run_pipeline,
)

INPUT_PATH  = "data/processed/gps_processed_events.csv"
OUTPUT_PATH = "data/processed/map_matched_events.csv"

# ---------------------------------------------------------------------------
# 1. Input file exists
# ---------------------------------------------------------------------------

def test_input_file_exists():
    assert os.path.exists(INPUT_PATH), f"Input file missing: {INPUT_PATH}"


# ---------------------------------------------------------------------------
# 2. Route segments are defined and well-formed
# ---------------------------------------------------------------------------

def test_route_segments_defined():
    assert len(ROUTE_SEGMENTS) >= 1, "ROUTE_SEGMENTS must not be empty"


def test_route_segments_structure():
    for seg in ROUTE_SEGMENTS:
        for key in ("segment_id", "start_lat", "start_lon", "end_lat", "end_lon", "mid_lat", "mid_lon"):
            assert key in seg, f"Segment missing key '{key}': {seg}"
        # Midpoint should be between start and end
        assert min(seg["start_lat"], seg["end_lat"]) <= seg["mid_lat"] <= max(seg["start_lat"], seg["end_lat"])
        assert min(seg["start_lon"], seg["end_lon"]) <= seg["mid_lon"] <= max(seg["start_lon"], seg["end_lon"])


# ---------------------------------------------------------------------------
# 3. Haversine distance sanity checks
# ---------------------------------------------------------------------------

def test_haversine_distance_same_point():
    d = haversine_distance(9.93, 76.27, 9.93, 76.27)
    assert d == pytest.approx(0.0, abs=1e-6)


def test_haversine_distance_known_value():
    # 1 degree of latitude at the equator ≈ 111 320 m
    # At lat ~9.9 N, 1 degree latitude ≈ 111 300 m (very close to equatorial value)
    d = haversine_distance(9.93, 76.27, 10.93, 76.27)
    assert 110_000 < d < 112_000, f"Unexpected 1-degree latitude distance: {d:.0f} m"


def test_haversine_distance_non_negative():
    d = haversine_distance(9.93, 76.27, 9.94, 76.28)
    assert d >= 0


# ---------------------------------------------------------------------------
# 4. Valid coordinates can be matched
# ---------------------------------------------------------------------------

def test_valid_coordinate_matches():
    seg_id, dist, status = match_event_to_segment(
        lat=9.932, lon=76.268, gps_valid=1, inside_route_area=1
    )
    assert status == "matched"
    assert seg_id is not None
    assert dist is not None and dist >= 0


# ---------------------------------------------------------------------------
# 5. Invalid / outside coordinates are not matched
# ---------------------------------------------------------------------------

def test_invalid_gps_returns_correct_status():
    seg_id, dist, status = match_event_to_segment(
        lat=math.nan, lon=76.268, gps_valid=0, inside_route_area=0
    )
    assert status == "invalid_gps"
    assert seg_id is None
    assert dist is None


def test_outside_route_returns_correct_status():
    seg_id, dist, status = match_event_to_segment(
        lat=8.00, lon=75.00, gps_valid=1, inside_route_area=0
    )
    assert status == "outside_route"
    assert seg_id is None
    assert dist is None


# ---------------------------------------------------------------------------
# 6. A known point near a specific segment maps to that segment
# ---------------------------------------------------------------------------
#
# Manually verified:
#   The midpoint of segment_014 (first segment) is approximately:
#       lat = (9.931224 + 9.932196) / 2 = 9.931710
#       lon = (76.267341 + 76.268269) / 2 = 76.267805
#
#   A point placed exactly at that midpoint should be closest to segment_014,
#   not to any other segment (all others are further away).
#
def test_known_point_matches_nearest_segment():
    # Build expected midpoint of segment_014
    first_seg = ROUTE_SEGMENTS[0]
    assert first_seg["segment_id"] == "segment_014", (
        f"First segment expected 'segment_014', got '{first_seg['segment_id']}'"
    )
    lat_probe = first_seg["mid_lat"]
    lon_probe = first_seg["mid_lon"]

    seg_id, dist, status = match_event_to_segment(
        lat=lat_probe, lon=lon_probe, gps_valid=1, inside_route_area=1
    )
    assert status == "matched"
    assert seg_id == "segment_014", f"Expected segment_014, got {seg_id}"
    assert dist == pytest.approx(0.0, abs=1e-3), f"Distance to own midpoint should be ~0, got {dist}"


def test_point_near_last_segment():
    last_seg = ROUTE_SEGMENTS[-1]
    lat_probe = last_seg["mid_lat"]
    lon_probe = last_seg["mid_lon"]
    seg_id, _, status = match_event_to_segment(
        lat=lat_probe, lon=lon_probe, gps_valid=1, inside_route_area=1
    )
    assert status == "matched"
    assert seg_id == last_seg["segment_id"]


# ---------------------------------------------------------------------------
# 7 & 8. Every valid in-route event has a road_segment_id and valid status
# ---------------------------------------------------------------------------

def _load_and_process():
    """Helper: load real input and run pipeline into a tmp location."""
    if not os.path.exists(INPUT_PATH):
        pytest.skip(f"Input file not found: {INPUT_PATH}")
    df = pd.read_csv(INPUT_PATH)
    return process_map_matching(df)


def test_all_valid_events_have_segment_id():
    df_out = _load_and_process()
    valid_mask = (df_out["gps_valid"] == 1) & (df_out["inside_route_area"] == 1)
    for _, row in df_out[valid_mask].iterrows():
        assert pd.notna(row["road_segment_id"]), f"Missing segment for {row['event_id']}"


def test_all_valid_events_have_matched_status():
    df_out = _load_and_process()
    valid_mask = (df_out["gps_valid"] == 1) & (df_out["inside_route_area"] == 1)
    for _, row in df_out[valid_mask].iterrows():
        assert row["map_match_status"] == "matched", (
            f"Expected 'matched' for {row['event_id']}, got {row['map_match_status']}"
        )


# ---------------------------------------------------------------------------
# 9. Matching distance is non-negative for matched events
# ---------------------------------------------------------------------------

def test_matching_distance_non_negative():
    df_out = _load_and_process()
    matched = df_out[df_out["map_match_status"] == "matched"]
    assert (matched["map_match_distance_m"] >= 0).all()


def test_no_nan_or_inf_distance_for_matched_events():
    df_out = _load_and_process()
    matched = df_out[df_out["map_match_status"] == "matched"]
    assert not matched["map_match_distance_m"].isna().any()
    assert not np.isinf(matched["map_match_distance_m"]).any()


# ---------------------------------------------------------------------------
# 10. Output file is created and has same row count + unchanged event IDs
# ---------------------------------------------------------------------------

def test_pipeline_creates_output_file(tmp_path):
    if not os.path.exists(INPUT_PATH):
        pytest.skip(f"Input file not found: {INPUT_PATH}")
    output_path = str(tmp_path / "map_matched_events.csv")
    run_pipeline(INPUT_PATH, output_path)
    assert os.path.exists(output_path)


def test_output_row_count_equals_input(tmp_path):
    if not os.path.exists(INPUT_PATH):
        pytest.skip(f"Input file not found: {INPUT_PATH}")
    df_in = pd.read_csv(INPUT_PATH)
    output_path = str(tmp_path / "map_matched_events.csv")
    run_pipeline(INPUT_PATH, output_path)
    df_out = pd.read_csv(output_path)
    assert len(df_out) == len(df_in), (
        f"Row count changed: input={len(df_in)}, output={len(df_out)}"
    )


def test_event_ids_unchanged(tmp_path):
    if not os.path.exists(INPUT_PATH):
        pytest.skip(f"Input file not found: {INPUT_PATH}")
    df_in  = pd.read_csv(INPUT_PATH)
    output_path = str(tmp_path / "map_matched_events.csv")
    run_pipeline(INPUT_PATH, output_path)
    df_out = pd.read_csv(output_path)
    assert list(df_in["event_id"]) == list(df_out["event_id"]), "event_id column was altered"


# ---------------------------------------------------------------------------
# 11. Results are deterministic
# ---------------------------------------------------------------------------

def test_results_are_deterministic():
    df_out_a = _load_and_process()
    df_out_b = _load_and_process()
    pd.testing.assert_frame_equal(df_out_a, df_out_b)


# ---------------------------------------------------------------------------
# 12. Ground truth columns are not introduced
# ---------------------------------------------------------------------------

def test_ground_truth_not_used():
    df_out = _load_and_process()
    assert "ground_truth_event" not in df_out.columns, (
        "ground_truth_event must not appear in map-matched output"
    )
    assert "ground_truth_type" not in df_out.columns, (
        "ground_truth_type must not appear in map-matched output"
    )


# ---------------------------------------------------------------------------
# 13. Required output columns exist
# ---------------------------------------------------------------------------

def test_required_output_columns():
    df_out = _load_and_process()
    for col in ("road_segment_id", "map_match_distance_m", "map_match_status"):
        assert col in df_out.columns, f"Missing output column: {col}"


# ---------------------------------------------------------------------------
# CLI standalone runner (not collected by pytest)
# ---------------------------------------------------------------------------

def run():
    print("Running test_map_matching.py standalone checks...")
    test_input_file_exists()
    print("  [OK] Input file exists")
    test_route_segments_defined()
    test_route_segments_structure()
    print(f"  [OK] {len(ROUTE_SEGMENTS)} route segments defined and well-formed")
    test_haversine_distance_same_point()
    test_haversine_distance_known_value()
    test_haversine_distance_non_negative()
    print("  [OK] Haversine distance is correct")
    test_valid_coordinate_matches()
    print("  [OK] Valid coords are matched")
    test_invalid_gps_returns_correct_status()
    test_outside_route_returns_correct_status()
    print("  [OK] Invalid/outside coords are not matched")
    test_known_point_matches_nearest_segment()
    test_point_near_last_segment()
    print("  [OK] Known anchor points match their expected segments")
    test_all_valid_events_have_segment_id()
    test_all_valid_events_have_matched_status()
    print("  [OK] All valid events have segment ID and 'matched' status")
    test_matching_distance_non_negative()
    test_no_nan_or_inf_distance_for_matched_events()
    print("  [OK] Matching distances are finite and non-negative")
    test_results_are_deterministic()
    print("  [OK] Results are deterministic")
    test_ground_truth_not_used()
    print("  [OK] Ground truth columns not present in output")
    test_required_output_columns()
    print("  [OK] Required output columns present")
    print("All map matching tests passed!")


if __name__ == "__main__":
    run()
