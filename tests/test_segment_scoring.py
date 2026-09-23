"""
Tests for M11: Severity + Confidence Scoring
==============================================
Every test_* function is collected by pytest automatically.
The run() function at the bottom is a standalone CLI checker.
"""

import os
import math
import pytest
import numpy as np
import pandas as pd

from src.processing.score_segments import (
    TOTAL_PASSES,
    POTHOLE_WEIGHT,
    SPEED_BREAKER_WEIGHT,
    ROUGH_ROAD_WEIGHT,
    SEVERITY_CAP,
    CONF_VERY_HIGH,
    CONF_HIGH,
    CONF_MODERATE,
    SEV_CRITICAL,
    SEV_HIGH,
    SEV_MODERATE,
    compute_confidence,
    confidence_label,
    compute_raw_severity,
    compute_severity_score,
    severity_label,
    primary_condition,
    score_segments,
    load_aggregated_segments,
    run_pipeline,
)

INPUT_PATH  = "data/processed/aggregated_segments.csv"
OUTPUT_PATH = "data/processed/scored_segments.csv"

# ---------------------------------------------------------------------------
# Hand-built reference DataFrame (from the spec)
#
#   segment_A:
#     pothole_count=2, speed_breaker_count=0, rough_road_count=1
#     total_event_count=3, unique_pass_count=2
#
#   Expected:
#     raw_severity      = 2*3 + 0*1 + 1*2 = 8
#     severity_score    = min(8/12, 1.0)*100 = 66.666... -> "high"
#     confidence_score  = 2/4 = 0.50          -> "high"
#     confidence_percent = 50
#     primary_condition = "pothole"
# ---------------------------------------------------------------------------

_HAND_DF = pd.DataFrame({
    "road_segment_id":      ["segment_A",  "segment_B"],
    "total_event_count":    [3,             1          ],
    "unique_pass_count":    [2,             1          ],
    "pothole_count":        [2,             0          ],
    "speed_breaker_count":  [0,             1          ],
    "rough_road_count":     [1,             0          ],
    "pass_ids":             ["1,2",         "3"        ],
    "event_types_observed": ["pothole,rough_road", "speed_breaker"],
})


# ============================================================
# 1. Input file
# ============================================================

def test_input_file_exists():
    assert os.path.exists(INPUT_PATH), f"Missing: {INPUT_PATH}"


# ============================================================
# 2. Confidence formula
# ============================================================

def test_confidence_score_formula():
    assert compute_confidence(2, total_passes=4) == pytest.approx(0.50)
    assert compute_confidence(4, total_passes=4) == pytest.approx(1.00)
    assert compute_confidence(1, total_passes=4) == pytest.approx(0.25)
    assert compute_confidence(3, total_passes=4) == pytest.approx(0.75)


def test_confidence_percent_conversion():
    row = score_segments(_HAND_DF).iloc[0]  # segment_A, unique_pass_count=2
    assert row["confidence_score"]   == pytest.approx(0.50, abs=1e-6)
    assert row["confidence_percent"] == pytest.approx(50.0, abs=1e-6)


def test_confidence_never_exceeds_one():
    scored = score_segments(_HAND_DF)
    assert (scored["confidence_score"] <= 1.0).all()


def test_confidence_exceeds_total_passes_raises():
    bad = _HAND_DF.copy()
    # Make counts internally consistent but unique_pass_count > TOTAL_PASSES
    bad.loc[0, "unique_pass_count"]   = 5   # exceeds total_passes=4
    bad.loc[0, "total_event_count"]   = 5
    bad.loc[0, "pothole_count"]       = 5
    bad.loc[0, "speed_breaker_count"] = 0
    bad.loc[0, "rough_road_count"]    = 0
    with pytest.raises(ValueError, match="TOTAL_PASSES"):
        score_segments(bad, total_passes=4)


# ============================================================
# 3. Confidence labels at boundaries
# ============================================================

def test_confidence_label_very_high():
    assert confidence_label(0.75) == "very_high"
    assert confidence_label(1.00) == "very_high"
    assert confidence_label(0.99) == "very_high"


def test_confidence_label_high():
    assert confidence_label(0.50) == "high"
    assert confidence_label(0.74) == "high"


def test_confidence_label_moderate():
    assert confidence_label(0.25) == "moderate"
    assert confidence_label(0.49) == "moderate"


def test_confidence_label_low():
    assert confidence_label(0.00) == "low"
    assert confidence_label(0.24) == "low"


# ============================================================
# 4. Severity formula
# ============================================================

def test_raw_severity_formula():
    # 2*3 + 0*1 + 1*2 = 8
    assert compute_raw_severity(2, 0, 1) == 8

def test_raw_severity_all_types():
    # 1*3 + 2*1 + 3*2 = 3+2+6 = 11
    assert compute_raw_severity(1, 2, 3) == 11

def test_severity_score_normalisation():
    # raw=8, cap=12 -> min(8/12, 1)*100 = 66.666...
    assert compute_severity_score(8, cap=12) == pytest.approx(66.6667, abs=0.01)


def test_severity_score_capped_at_100():
    assert compute_severity_score(100, cap=12) == pytest.approx(100.0)


def test_severity_never_exceeds_100():
    scored = score_segments(_HAND_DF)
    assert (scored["severity_score"] <= 100.0).all()


def test_hand_df_segment_a_severity():
    scored = score_segments(_HAND_DF)
    row = scored[scored["road_segment_id"] == "segment_A"].iloc[0]
    assert row["raw_severity"]   == 8
    assert row["severity_score"] == pytest.approx(66.6667, abs=0.01)
    assert row["severity_label"] == "high"


# ============================================================
# 5. Severity does NOT depend on pass count
# ============================================================

def test_severity_independent_of_pass_count():
    """
    Two rows with identical event counts but different unique_pass_count.
    Their severity_score must be identical; only confidence_score may differ.
    """
    df = pd.DataFrame({
        "road_segment_id":     ["seg_x", "seg_y"],
        "total_event_count":   [2,         2    ],
        "unique_pass_count":   [1,         4    ],   # different passes
        "pothole_count":       [2,         2    ],   # same events
        "speed_breaker_count": [0,         0    ],
        "rough_road_count":    [0,         0    ],
        "pass_ids":            ["1",       "1,2,3,4"],
        "event_types_observed":["pothole", "pothole"],
    })
    scored = score_segments(df, total_passes=4)
    row_x = scored[scored["road_segment_id"] == "seg_x"].iloc[0]
    row_y = scored[scored["road_segment_id"] == "seg_y"].iloc[0]

    assert row_x["severity_score"] == pytest.approx(row_y["severity_score"], abs=1e-6), \
        "Severity must not change when only pass count changes"
    assert row_x["confidence_score"] != row_y["confidence_score"], \
        "Confidence must differ when pass count differs"


# ============================================================
# 6. Severity labels at boundaries
# ============================================================

def test_severity_label_critical():
    assert severity_label(75)  == "critical"
    assert severity_label(100) == "critical"
    assert severity_label(99)  == "critical"


def test_severity_label_high():
    assert severity_label(50) == "high"
    assert severity_label(74) == "high"


def test_severity_label_moderate():
    assert severity_label(25) == "moderate"
    assert severity_label(49) == "moderate"


def test_severity_label_low():
    assert severity_label(0)  == "low"
    assert severity_label(24) == "low"


# ============================================================
# 7. Primary condition selection and tie-breaking
# ============================================================

def test_primary_condition_highest_wins():
    assert primary_condition(3, 1, 1, 5) == "pothole"   # pothole highest
    assert primary_condition(1, 1, 3, 5) == "rough_road"  # rough_road highest
    assert primary_condition(0, 4, 1, 5) == "speed_breaker"


def test_primary_condition_tie_pothole_beats_rough():
    # pothole=2, rough_road=2 -> pothole wins (priority 0 vs 1)
    assert primary_condition(2, 0, 2, 4) == "pothole"


def test_primary_condition_tie_rough_beats_speed_breaker():
    # rough_road=2, speed_breaker=2 -> rough_road wins (priority 1 vs 2)
    assert primary_condition(0, 2, 2, 4) == "rough_road"


def test_primary_condition_zero_events():
    assert primary_condition(0, 0, 0, 0) == "none"


def test_primary_condition_in_dataframe():
    scored = score_segments(_HAND_DF)
    row_a = scored[scored["road_segment_id"] == "segment_A"].iloc[0]
    assert row_a["primary_condition"] == "pothole"  # pothole=2 > rough=1

    row_b = scored[scored["road_segment_id"] == "segment_B"].iloc[0]
    assert row_b["primary_condition"] == "speed_breaker"


# ============================================================
# 8. Missing required columns handled clearly
# ============================================================

def test_missing_column_raises():
    bad = _HAND_DF.drop(columns=["pothole_count"])
    with pytest.raises(ValueError, match="missing required columns"):
        score_segments(bad)


# ============================================================
# 9. Event-count consistency check
# ============================================================

def test_inconsistent_event_counts_raises():
    bad = _HAND_DF.copy()
    bad.loc[0, "pothole_count"] = 99  # doesn't match total_event_count=3
    with pytest.raises(ValueError, match="total_event_count"):
        score_segments(bad)


# ============================================================
# 10. Output structure
# ============================================================

def test_required_output_columns():
    scored = score_segments(_HAND_DF)
    for col in ("raw_severity", "severity_score", "severity_label",
                "confidence_score", "confidence_percent", "confidence_label",
                "primary_condition"):
        assert col in scored.columns, f"Missing column: {col}"


def test_one_row_per_segment():
    scored = score_segments(_HAND_DF)
    assert scored["road_segment_id"].is_unique


def test_m10_columns_preserved():
    scored = score_segments(_HAND_DF)
    for col in _HAND_DF.columns:
        assert col in scored.columns, f"M10 column lost: {col}"


def test_m10_counts_unchanged():
    scored = score_segments(_HAND_DF)
    for col in ("pothole_count", "speed_breaker_count", "rough_road_count",
                "total_event_count", "unique_pass_count"):
        pd.testing.assert_series_equal(
            scored.set_index("road_segment_id")[col].sort_index(),
            _HAND_DF.set_index("road_segment_id")[col].sort_index(),
            check_names=False,
        )


# ============================================================
# 11. No NaN / inf
# ============================================================

def test_no_nan_values():
    scored = score_segments(_HAND_DF)
    numeric_cols = ["raw_severity", "severity_score",
                    "confidence_score", "confidence_percent"]
    for col in numeric_cols:
        assert not scored[col].isna().any(), f"NaN in {col}"


def test_no_inf_values():
    scored = score_segments(_HAND_DF)
    numeric_cols = ["raw_severity", "severity_score",
                    "confidence_score", "confidence_percent"]
    for col in numeric_cols:
        assert not np.isinf(scored[col]).any(), f"Inf in {col}"


# ============================================================
# 12. Ground truth not introduced
# ============================================================

def test_ground_truth_not_introduced():
    scored = score_segments(_HAND_DF)
    assert "ground_truth_event" not in scored.columns
    assert "ground_truth_type"  not in scored.columns


# ============================================================
# 13. Determinism
# ============================================================

def test_deterministic():
    a = score_segments(_HAND_DF)
    b = score_segments(_HAND_DF)
    pd.testing.assert_frame_equal(a, b)


# ============================================================
# 14. Real data end-to-end tests
# ============================================================

def _load_and_score():
    if not os.path.exists(INPUT_PATH):
        pytest.skip(f"Input file not found: {INPUT_PATH}")
    df = load_aggregated_segments(INPUT_PATH)
    return df, score_segments(df)


def test_real_output_created(tmp_path):
    if not os.path.exists(INPUT_PATH):
        pytest.skip(f"Input file not found: {INPUT_PATH}")
    out = str(tmp_path / "scored.csv")
    run_pipeline(INPUT_PATH, out)
    assert os.path.exists(out)


def test_real_one_row_per_segment():
    _, scored = _load_and_score()
    assert scored["road_segment_id"].is_unique


def test_real_all_segments_preserved():
    df, scored = _load_and_score()
    assert set(df["road_segment_id"]) == set(scored["road_segment_id"])


def test_real_event_counts_unchanged():
    df, scored = _load_and_score()
    for col in ("pothole_count", "speed_breaker_count", "rough_road_count",
                "total_event_count"):
        pd.testing.assert_series_equal(
            scored.set_index("road_segment_id")[col].sort_index(),
            df.set_index("road_segment_id")[col].sort_index(),
            check_names=False,
        )


def test_real_no_nan_or_inf():
    _, scored = _load_and_score()
    for col in ("raw_severity", "severity_score", "confidence_score", "confidence_percent"):
        assert not scored[col].isna().any(), f"NaN in {col}"
        assert not np.isinf(scored[col]).any(), f"Inf in {col}"


def test_real_ground_truth_absent():
    _, scored = _load_and_score()
    assert "ground_truth_event" not in scored.columns
    assert "ground_truth_type"  not in scored.columns


def test_real_output_row_count(tmp_path):
    df, _ = _load_and_score()
    out = str(tmp_path / "scored.csv")
    run_pipeline(INPUT_PATH, out)
    out_df = pd.read_csv(out)
    assert len(out_df) == len(df)


# ============================================================
# CLI standalone runner
# ============================================================

def run():
    print("Running test_segment_scoring.py standalone checks...")

    test_input_file_exists()
    print("  [OK] Input file exists")

    test_confidence_score_formula()
    test_confidence_percent_conversion()
    test_confidence_never_exceeds_one()
    print("  [OK] Confidence formula and percent conversion correct")

    test_confidence_label_very_high()
    test_confidence_label_high()
    test_confidence_label_moderate()
    test_confidence_label_low()
    print("  [OK] Confidence labels at all boundaries")

    test_raw_severity_formula()
    test_raw_severity_all_types()
    test_severity_score_normalisation()
    test_severity_score_capped_at_100()
    test_severity_never_exceeds_100()
    test_hand_df_segment_a_severity()
    print("  [OK] Severity formula, cap, and normalisation correct")

    test_severity_independent_of_pass_count()
    print("  [OK] Severity is independent of pass count")

    test_severity_label_critical()
    test_severity_label_high()
    test_severity_label_moderate()
    test_severity_label_low()
    print("  [OK] Severity labels at all boundaries")

    test_primary_condition_highest_wins()
    test_primary_condition_tie_pothole_beats_rough()
    test_primary_condition_tie_rough_beats_speed_breaker()
    test_primary_condition_zero_events()
    test_primary_condition_in_dataframe()
    print("  [OK] Primary condition selection and tie-breaking")

    test_missing_column_raises()
    test_inconsistent_event_counts_raises()
    print("  [OK] Input validation raises on bad data")

    test_required_output_columns()
    test_one_row_per_segment()
    test_m10_columns_preserved()
    test_m10_counts_unchanged()
    print("  [OK] Output structure and column preservation")

    test_no_nan_values()
    test_no_inf_values()
    print("  [OK] No NaN or Inf in numeric outputs")

    test_ground_truth_not_introduced()
    print("  [OK] Ground truth columns not introduced")

    test_deterministic()
    print("  [OK] Results are deterministic")

    test_real_one_row_per_segment()
    test_real_all_segments_preserved()
    test_real_event_counts_unchanged()
    test_real_no_nan_or_inf()
    test_real_ground_truth_absent()
    print("  [OK] Real data integrity verified")

    print("All segment scoring tests passed!")


if __name__ == "__main__":
    run()
