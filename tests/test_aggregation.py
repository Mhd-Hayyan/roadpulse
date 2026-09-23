"""
Tests for M10: Multi-Pass Aggregation
=======================================
Every test_* function is collected by pytest automatically.
The run() function at the bottom is a standalone CLI checker.
"""

import os
import pytest
import numpy as np
import pandas as pd

from src.aggregation.aggregation import (
    aggregate_segments,
    load_map_matched_events,
    save_aggregated_segments,
    run_pipeline,
    ROAD_EVENT_TYPES,
)

INPUT_PATH  = "data/processed/map_matched_events.csv"
OUTPUT_PATH = "data/processed/aggregated_segments.csv"

# ---------------------------------------------------------------------------
# Manually constructed reference DataFrame
# This verifies logic, not just the current dataset.
#
#   pass 1 -> segment_test -> pothole
#   pass 2 -> segment_test -> pothole
#   pass 3 -> segment_test -> rough_road
#   pass 3 -> segment_test -> speed_breaker   <-- same pass, second event
#
# Expected:
#   total_event_count   = 4
#   unique_pass_count   = 3   (passes 1, 2, 3 — pass 3 counted once)
#   pothole_count       = 2
#   rough_road_count    = 1
#   speed_breaker_count = 1
# ---------------------------------------------------------------------------

_MANUAL_DF = pd.DataFrame({
    "event_id":         ["e1", "e2", "e3", "e4"],
    "pass_id":          [1,    2,    3,    3   ],
    "event_type":       ["pothole", "pothole", "rough_road", "speed_breaker"],
    "road_segment_id":  ["segment_test"] * 4,
    "map_match_status": ["matched"] * 4,
})

# A second segment for multi-segment tests
_MULTI_SEG_DF = pd.DataFrame({
    "event_id":         ["e1", "e2", "e3", "e4", "e5"],
    "pass_id":          [1,    2,    1,    2,    3   ],
    "event_type":       ["pothole", "pothole", "speed_breaker", "speed_breaker", "rough_road"],
    "road_segment_id":  ["seg_A", "seg_A", "seg_B", "seg_B", "seg_B"],
    "map_match_status": ["matched"] * 5,
})

# Events with invalid/outside statuses — must be excluded
_MIXED_STATUS_DF = pd.DataFrame({
    "event_id":         ["e1", "e2", "e3"],
    "pass_id":          [1,    2,    3   ],
    "event_type":       ["pothole", "pothole", "rough_road"],
    "road_segment_id":  ["seg_X", "seg_X", "seg_X"],
    "map_match_status": ["matched", "invalid_gps", "outside_route"],
})


# ---------------------------------------------------------------------------
# 1. Input file exists
# ---------------------------------------------------------------------------

def test_input_file_exists():
    assert os.path.exists(INPUT_PATH), f"Input file missing: {INPUT_PATH}"


# ---------------------------------------------------------------------------
# 2–3. Manual logic test: counts are correct, pass 3 not double-counted
# ---------------------------------------------------------------------------

def test_manual_total_event_count():
    agg = aggregate_segments(_MANUAL_DF)
    row = agg[agg["road_segment_id"] == "segment_test"].iloc[0]
    assert row["total_event_count"] == 4


def test_manual_unique_pass_count_not_double_counted():
    agg = aggregate_segments(_MANUAL_DF)
    row = agg[agg["road_segment_id"] == "segment_test"].iloc[0]
    # Pass 3 appears in two events but must be counted only once
    assert row["unique_pass_count"] == 3, (
        f"Expected 3 unique passes, got {row['unique_pass_count']}. "
        "Pass 3 must not be counted twice."
    )


def test_manual_pothole_count():
    agg = aggregate_segments(_MANUAL_DF)
    row = agg[agg["road_segment_id"] == "segment_test"].iloc[0]
    assert row["pothole_count"] == 2


def test_manual_rough_road_count():
    agg = aggregate_segments(_MANUAL_DF)
    row = agg[agg["road_segment_id"] == "segment_test"].iloc[0]
    assert row["rough_road_count"] == 1


def test_manual_speed_breaker_count():
    agg = aggregate_segments(_MANUAL_DF)
    row = agg[agg["road_segment_id"] == "segment_test"].iloc[0]
    assert row["speed_breaker_count"] == 1


# ---------------------------------------------------------------------------
# 4. One row per unique road_segment_id (no duplicates)
# ---------------------------------------------------------------------------

def test_one_row_per_segment_manual():
    agg = aggregate_segments(_MANUAL_DF)
    assert agg["road_segment_id"].is_unique


def test_one_row_per_segment_multi():
    agg = aggregate_segments(_MULTI_SEG_DF)
    assert agg["road_segment_id"].is_unique


# ---------------------------------------------------------------------------
# 5. Multi-segment aggregation correctness
# ---------------------------------------------------------------------------

def test_multi_segment_seg_a():
    agg = aggregate_segments(_MULTI_SEG_DF)
    row = agg[agg["road_segment_id"] == "seg_A"].iloc[0]
    assert row["total_event_count"] == 2
    assert row["unique_pass_count"] == 2
    assert row["pothole_count"] == 2
    assert row["speed_breaker_count"] == 0
    assert row["rough_road_count"] == 0


def test_multi_segment_seg_b():
    agg = aggregate_segments(_MULTI_SEG_DF)
    row = agg[agg["road_segment_id"] == "seg_B"].iloc[0]
    assert row["total_event_count"] == 3
    # seg_B events: pass 1 speed_breaker, pass 2 speed_breaker, pass 3 rough_road -> 3 distinct passes
    assert row["unique_pass_count"] == 3
    assert row["speed_breaker_count"] == 2
    assert row["rough_road_count"] == 1
    assert row["pothole_count"] == 0


# ---------------------------------------------------------------------------
# 6. Invalid/unmatched events are excluded
# ---------------------------------------------------------------------------

def test_invalid_events_excluded():
    agg = aggregate_segments(_MIXED_STATUS_DF)
    assert len(agg) > 0
    row = agg[agg["road_segment_id"] == "seg_X"].iloc[0]
    # Only the 'matched' event (pass 1) should be counted
    assert row["total_event_count"] == 1
    assert row["unique_pass_count"] == 1
    assert row["pothole_count"] == 1


# ---------------------------------------------------------------------------
# 7. pass_ids string is deterministic and sorted
# ---------------------------------------------------------------------------

def test_pass_ids_string_sorted_and_correct():
    agg = aggregate_segments(_MANUAL_DF)
    row = agg[agg["road_segment_id"] == "segment_test"].iloc[0]
    assert row["pass_ids"] == "1,2,3"


# ---------------------------------------------------------------------------
# 8. event_types_observed is sorted and correct
# ---------------------------------------------------------------------------

def test_event_types_observed_sorted():
    agg = aggregate_segments(_MANUAL_DF)
    row = agg[agg["road_segment_id"] == "segment_test"].iloc[0]
    assert row["event_types_observed"] == "pothole,rough_road,speed_breaker"


# ---------------------------------------------------------------------------
# 9. Ground truth columns are NOT introduced
# ---------------------------------------------------------------------------

def test_ground_truth_not_introduced():
    agg = aggregate_segments(_MANUAL_DF)
    assert "ground_truth_event" not in agg.columns
    assert "ground_truth_type"  not in agg.columns


# ---------------------------------------------------------------------------
# 10. No NaN / inf in required numeric columns
# ---------------------------------------------------------------------------

def test_no_nan_in_counts():
    agg = aggregate_segments(_MANUAL_DF)
    for col in ("total_event_count", "unique_pass_count",
                "pothole_count", "speed_breaker_count", "rough_road_count"):
        assert not agg[col].isna().any(),  f"NaN in {col}"
        assert not agg[col].isin([float("inf"), float("-inf")]).any(), f"Inf in {col}"


# ---------------------------------------------------------------------------
# 11. Required output columns exist
# ---------------------------------------------------------------------------

def test_required_output_columns():
    agg = aggregate_segments(_MANUAL_DF)
    required = [
        "road_segment_id", "total_event_count", "unique_pass_count",
        "pothole_count", "speed_breaker_count", "rough_road_count",
        "pass_ids", "event_types_observed",
    ]
    for col in required:
        assert col in agg.columns, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# 12. Aggregation is deterministic across two runs
# ---------------------------------------------------------------------------

def test_aggregation_is_deterministic():
    a = aggregate_segments(_MULTI_SEG_DF)
    b = aggregate_segments(_MULTI_SEG_DF)
    pd.testing.assert_frame_equal(a, b)


# ---------------------------------------------------------------------------
# 13–15. Real data end-to-end checks
# ---------------------------------------------------------------------------

def _load_real_agg():
    if not os.path.exists(INPUT_PATH):
        pytest.skip(f"Input file not found: {INPUT_PATH}")
    df = load_map_matched_events(INPUT_PATH)
    return df, aggregate_segments(df)


def test_real_no_segment_lost():
    df, agg = _load_real_agg()
    input_segments  = set(df[df["map_match_status"] == "matched"]["road_segment_id"].unique())
    output_segments = set(agg["road_segment_id"])
    assert input_segments == output_segments, (
        f"Segments missing from output: {input_segments - output_segments}"
    )


def test_real_no_new_segment_invented():
    df, agg = _load_real_agg()
    input_segments  = set(df[df["map_match_status"] == "matched"]["road_segment_id"].unique())
    output_segments = set(agg["road_segment_id"])
    assert output_segments.issubset(input_segments), (
        f"Invented segments: {output_segments - input_segments}"
    )


def test_real_total_event_count_correct():
    df, agg = _load_real_agg()
    valid = df[df["map_match_status"] == "matched"]
    input_counts = valid.groupby("road_segment_id").size()
    for seg_id, expected in input_counts.items():
        actual = agg[agg["road_segment_id"] == seg_id]["total_event_count"].iloc[0]
        assert actual == expected, (
            f"Segment {seg_id}: expected {expected} events, got {actual}"
        )


def test_real_unique_pass_count_correct():
    df, agg = _load_real_agg()
    valid = df[df["map_match_status"] == "matched"]
    for seg_id, group in valid.groupby("road_segment_id"):
        expected = group["pass_id"].nunique()
        actual   = agg[agg["road_segment_id"] == seg_id]["unique_pass_count"].iloc[0]
        assert actual == expected, (
            f"Segment {seg_id}: expected {expected} unique passes, got {actual}"
        )


def test_real_output_file_created(tmp_path):
    if not os.path.exists(INPUT_PATH):
        pytest.skip(f"Input file not found: {INPUT_PATH}")
    out = str(tmp_path / "agg.csv")
    run_pipeline(INPUT_PATH, out)
    assert os.path.exists(out)


def test_real_output_row_count(tmp_path):
    if not os.path.exists(INPUT_PATH):
        pytest.skip(f"Input file not found: {INPUT_PATH}")
    df = load_map_matched_events(INPUT_PATH)
    n_segments = df[df["map_match_status"] == "matched"]["road_segment_id"].nunique()
    out = str(tmp_path / "agg.csv")
    run_pipeline(INPUT_PATH, out)
    agg = pd.read_csv(out)
    assert len(agg) == n_segments


# ---------------------------------------------------------------------------
# CLI standalone runner
# ---------------------------------------------------------------------------

def run():
    print("Running test_aggregation.py standalone checks...")

    test_input_file_exists()
    print("  [OK] Input file exists")

    test_manual_total_event_count()
    test_manual_unique_pass_count_not_double_counted()
    test_manual_pothole_count()
    test_manual_rough_road_count()
    test_manual_speed_breaker_count()
    print("  [OK] Manual logic: counts are correct, pass 3 not double-counted")

    test_one_row_per_segment_manual()
    test_one_row_per_segment_multi()
    print("  [OK] One row per unique road_segment_id")

    test_multi_segment_seg_a()
    test_multi_segment_seg_b()
    print("  [OK] Multi-segment aggregation correctness")

    test_invalid_events_excluded()
    print("  [OK] Invalid/outside events excluded")

    test_pass_ids_string_sorted_and_correct()
    print("  [OK] pass_ids string is sorted and correct")

    test_event_types_observed_sorted()
    print("  [OK] event_types_observed is sorted and correct")

    test_ground_truth_not_introduced()
    print("  [OK] Ground truth columns not introduced")

    test_no_nan_in_counts()
    print("  [OK] No NaN/Inf in count fields")

    test_required_output_columns()
    print("  [OK] All required output columns present")

    test_aggregation_is_deterministic()
    print("  [OK] Aggregation is deterministic")

    test_real_no_segment_lost()
    test_real_no_new_segment_invented()
    test_real_total_event_count_correct()
    test_real_unique_pass_count_correct()
    print("  [OK] Real data: segment integrity and count accuracy verified")

    print("All aggregation tests passed!")


if __name__ == "__main__":
    run()
