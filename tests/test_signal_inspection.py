"""
ROADPULSE — Signal Inspection Test Suite
=========================================
Validates that:
  1. The raw sensor CSV can be loaded.
  2. All required sensor columns exist.
  3. At least one pass can be selected from the dataset.
  4. The signal inspection module executes and produces expected plot files in data/processed/inspection/.
"""

import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.inspect_signals import load_dataset, compute_pass_summary, inspect_pass

CSV_PATH = PROJECT_ROOT / "data" / "raw" / "sensor_data.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "inspection"

EXPECTED_SENSOR_COLUMNS = [
    "timestamp", "pass_id", "latitude", "longitude",
    "accel_x", "accel_y", "accel_z",
    "gyro_x", "gyro_y", "gyro_z",
]


def _check(label, condition, detail=""):
    icon = "[PASS]" if condition else "[FAIL]"
    line = f"  {icon}  {label}"
    if not condition and detail:
        line += f"  -  {detail}"
    print(line)
    return condition


# ─── Pytest-compatible individual test functions ──────────────────────────────

def test_raw_csv_loads_successfully():
    df = load_dataset(CSV_PATH)
    assert isinstance(df, pd.DataFrame) and len(df) > 0

def test_expected_sensor_columns_exist():
    df = load_dataset(CSV_PATH)
    assert set(EXPECTED_SENSOR_COLUMNS).issubset(set(df.columns))

def test_at_least_one_pass_selectable():
    df = load_dataset(CSV_PATH)
    passes = df["pass_id"].unique()
    assert len(passes) >= 1

def test_pass_summary_computed_properly():
    df = load_dataset(CSV_PATH)
    summary = compute_pass_summary(df[df["pass_id"] == df["pass_id"].iloc[0]])
    assert summary["num_samples"] > 0 and summary["duration"] > 0

def test_inspection_produces_plot_files():
    test_out_dir = OUTPUT_DIR / "pytest_run"
    df = load_dataset(CSV_PATH)
    _, plot_files = inspect_pass(
        pass_id=int(df["pass_id"].iloc[0]),
        csv_path=CSV_PATH,
        output_dir=test_out_dir,
        save_plots=True,
    )
    assert len(plot_files) == 4 and all(p.exists() for p in plot_files)
    for p in plot_files:
        try:
            p.unlink()
        except Exception:
            pass
    try:
        test_out_dir.rmdir()
    except Exception:
        pass


# ─── Validation Runner ────────────────────────────────────────────────────────

def run():
    results = []

    print("\n==================================================")
    print("  ROADPULSE -- Signal Inspection Validation")
    print("==================================================")

    # 1. Raw CSV exists and can be loaded
    can_load = False
    df = None
    try:
        df = load_dataset(CSV_PATH)
        can_load = isinstance(df, pd.DataFrame) and len(df) > 0
    except Exception as e:
        can_load = False
    results.append(_check("Raw CSV loads successfully", can_load))

    if not can_load:
        print("\n[FATAL] Unable to load raw dataset. Exiting test.")
        sys.exit(1)

    # 2. Expected sensor columns exist
    missing_cols = set(EXPECTED_SENSOR_COLUMNS) - set(df.columns)
    results.append(_check(
        "Expected sensor columns exist",
        len(missing_cols) == 0,
        f"missing: {missing_cols}",
    ))

    # 3. At least one pass can be selected
    passes = df["pass_id"].unique()
    results.append(_check(
        "At least one pass can be selected",
        len(passes) >= 1,
        f"passes found: {passes}",
    ))

    # 4. Summary computation works
    pass_1_df = df[df["pass_id"] == passes[0]]
    summary = compute_pass_summary(pass_1_df)
    results.append(_check(
        "Pass summary computed properly",
        summary["num_samples"] > 0 and summary["duration"] > 0,
    ))

    # 5. Output directory and plot files can be produced
    test_out_dir = OUTPUT_DIR / "test_run"
    summary_res, plot_files = inspect_pass(
        pass_id=int(passes[0]),
        csv_path=CSV_PATH,
        output_dir=test_out_dir,
        save_plots=True,
    )
    all_files_exist = len(plot_files) == 4 and all(p.exists() for p in plot_files)
    results.append(_check(
        "Inspection function produces 4 plot files",
        all_files_exist,
        f"plots created: {[p.name for p in plot_files]}",
    ))

    # Clean up test_run files
    for p in plot_files:
        try:
            p.unlink()
        except Exception:
            pass
    try:
        test_out_dir.rmdir()
    except Exception:
        pass

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
