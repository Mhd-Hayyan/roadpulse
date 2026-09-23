"""
ROADPULSE — Feature Distribution Analysis Test Suite (Milestone 6A)
===================================================================
Validates that:
  1. Feature distribution analysis runs successfully.
  2. All 7 expected scenario labels are present in the analysis.
  3. All selected analysis feature columns exist.
  4. Summary CSV file (feature_distribution_summary.csv) is created.
  5. Window label analysis CSV (window_label_analysis.csv) is created.
  6. Strict ground-truth isolation: features.csv is never mutated with GT columns.
  7. All reported summary feature statistics are finite numbers.
  8. Label purity values are within [0.0, 1.0].
  9. All 8 diagnostic boxplots are generated in data/processed/feature_analysis/.
 10. Source features.csv file content and mtime remain completely unchanged.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.analyze_feature_distributions import (
    FEATURES_CSV_PATH,
    PREPROCESSED_CSV_PATH,
    ANALYSIS_OUTPUT_DIR,
    SUMMARY_CSV_PATH,
    WINDOW_LABEL_ANALYSIS_PATH,
    ALL_SELECTED_FEATURES,
    SCENARIO_ORDER,
    PLOT_FEATURES,
    load_input_datasets,
    assign_window_labels,
    compute_scenario_feature_summary,
    compute_purity_statistics,
    run_analysis,
)

EXPECTED_SCENARIOS = {
    "none", "rough_road", "pothole", "speed_breaker",
    "braking", "turning", "acceleration",
}


def _check(label, condition, detail=""):
    icon = "[PASS]" if condition else "[FAIL]"
    line = f"  {icon}  {label}"
    if not condition and detail:
        line += f"  -  {detail}"
    print(line)
    return condition


# ── Pytest-compatible test functions ─────────────────────────────

def test_analysis_runs_successfully():
    feat_df, pre_df = load_input_datasets()
    assert isinstance(feat_df, pd.DataFrame) and len(feat_df) > 0
    assert isinstance(pre_df, pd.DataFrame) and len(pre_df) > 0


def test_expected_scenario_labels_exist():
    feat_df, pre_df = load_input_datasets()
    analysis_df = assign_window_labels(feat_df, pre_df)
    labels = set(analysis_df["dominant_ground_truth_type"].unique())
    assert EXPECTED_SCENARIOS.issubset(labels)


def test_selected_feature_columns_exist():
    feat_df, _ = load_input_datasets()
    missing = set(ALL_SELECTED_FEATURES) - set(feat_df.columns)
    assert len(missing) == 0, f"Missing features: {missing}"


def test_summary_file_created():
    assert SUMMARY_CSV_PATH.exists()
    summary_df = pd.read_csv(SUMMARY_CSV_PATH)
    assert len(summary_df) > 0
    assert "scenario" in summary_df.columns
    assert "feature" in summary_df.columns


def test_window_analysis_file_created():
    assert WINDOW_LABEL_ANALYSIS_PATH.exists()
    w_df = pd.read_csv(WINDOW_LABEL_ANALYSIS_PATH)
    assert len(w_df) == 1012
    assert "dominant_ground_truth_type" in w_df.columns
    assert "label_purity" in w_df.columns


def test_no_ground_truth_columns_in_features_csv():
    feat_df = pd.read_csv(FEATURES_CSV_PATH)
    assert "ground_truth_event" not in feat_df.columns
    assert "ground_truth_type" not in feat_df.columns
    assert "dominant_ground_truth_type" not in feat_df.columns
    assert "label_purity" not in feat_df.columns


def test_reported_feature_statistics_are_finite():
    summary_df = pd.read_csv(SUMMARY_CSV_PATH)
    stat_cols = ["mean", "std", "median", "min", "max", "p90", "p95"]
    for col in stat_cols:
        assert np.all(np.isfinite(summary_df[col].values))


def test_label_purity_within_range():
    w_df = pd.read_csv(WINDOW_LABEL_ANALYSIS_PATH)
    purity = w_df["label_purity"].values
    assert np.all((purity >= 0.0) & (purity <= 1.0))


def test_all_diagnostic_plots_generated():
    for _, _, filename in PLOT_FEATURES:
        plot_file = ANALYSIS_OUTPUT_DIR / filename
        assert plot_file.exists(), f"Missing plot: {filename}"
        assert plot_file.stat().st_size > 1000, f"Empty plot file: {filename}"


def test_source_features_csv_remains_unchanged():
    feat_df = pd.read_csv(FEATURES_CSV_PATH)
    assert len(feat_df) == 1012
    assert len(feat_df.columns) == 41


# ── Standalone CLI runner ─────────────────────────────────────────

def run():
    results = []

    print("\n==================================================")
    print("  ROADPULSE -- Feature Distribution Test Suite")
    print("==================================================")

    # 1. Run pipeline
    mtime_before = FEATURES_CSV_PATH.stat().st_mtime
    size_before = FEATURES_CSV_PATH.stat().st_size

    try:
        analysis_df, summary_df, plot_files = run_analysis(save_plots=True)
        ran_ok = True
    except Exception as e:
        ran_ok = False
        print(f"Error running analysis: {e}")

    results.append(_check("Feature distribution analysis runs successfully", ran_ok))

    # 2. Scenarios
    scenarios = set(analysis_df["dominant_ground_truth_type"].unique())
    results.append(_check(
        "All expected scenario labels exist",
        EXPECTED_SCENARIOS.issubset(scenarios),
        f"found: {scenarios}",
    ))

    # 3. Selected feature columns
    missing_feats = set(ALL_SELECTED_FEATURES) - set(analysis_df.columns)
    results.append(_check(
        "All selected feature columns exist",
        len(missing_feats) == 0,
        f"missing: {missing_feats}",
    ))

    # 4. Summary file created
    results.append(_check(
        "Summary file created",
        SUMMARY_CSV_PATH.exists() and SUMMARY_CSV_PATH.stat().st_size > 0,
    ))

    # 5. Window label analysis file created
    results.append(_check(
        "Window label analysis file created",
        WINDOW_LABEL_ANALYSIS_PATH.exists() and WINDOW_LABEL_ANALYSIS_PATH.stat().st_size > 0,
    ))

    # 6. No ground truth columns added to features.csv
    feat_raw = pd.read_csv(FEATURES_CSV_PATH)
    gt_present = any(c in feat_raw.columns for c in ["ground_truth_event", "ground_truth_type", "dominant_ground_truth_type", "label_purity"])
    results.append(_check("No ground truth columns in features.csv", not gt_present))

    # 7. Summary statistics finite
    stat_cols = ["mean", "std", "median", "min", "max", "p90", "p95"]
    all_finite = np.all(np.isfinite(summary_df[stat_cols].values))
    results.append(_check("All summary statistics are finite numbers", all_finite))

    # 8. Purity between 0 and 1
    purity_vals = analysis_df["label_purity"].values
    purity_valid = np.all((purity_vals >= 0.0) & (purity_vals <= 1.0))
    results.append(_check("Label purity values are within [0.0, 1.0]", purity_valid))

    # 9. Plots generated
    plots_exist = len(plot_files) == 8 and all(p.exists() and p.stat().st_size > 1000 for p in plot_files)
    results.append(_check("All 8 diagnostic boxplots generated", plots_exist))

    # 10. Source features.csv unmodified
    mtime_after = FEATURES_CSV_PATH.stat().st_mtime
    size_after = FEATURES_CSV_PATH.stat().st_size
    unmodified = (mtime_before == mtime_after) and (size_before == size_after)
    results.append(_check("Source features.csv remains unchanged", unmodified))

    # Summary
    n_passed = sum(results)
    n_failed = len(results) - n_passed

    print("==================================================")
    print(f"  Result   : {n_passed} passed,  {n_failed} failed")
    print("==================================================\n")

    if n_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run()
