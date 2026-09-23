"""
ROADPULSE — Candidate Event Detection Pipeline
==============================================
Applies explainable, rule-based hierarchical gating to sensor-derived
window features to flag vehicle maneuver and road-surface anomaly candidates.

Detection Hierarchy:
--------------------
Gate 1 — Vehicle Dynamics (Maneuver Isolation):
  1. Turning:      gyro_z_max_abs > 0.025 AND accel_x_max_abs > 0.30
                   -> label: turning_candidate
  2. Braking:      accel_y_mean < -0.50
                   -> label: braking_candidate
  3. Acceleration: accel_y_mean > 0.25
                   -> label: acceleration_candidate

Gate 2 — Road-Surface Candidates (Vertical Shock Dynamics):
  4. Speed Breaker: accel_z_peak_to_peak > 1.60
                   -> label: speed_breaker_candidate
  5. Pothole:       accel_z_max_abs_diff > 0.20
                    AND accel_z_peak_to_peak / accel_z_std > 4.0
                   -> label: pothole_candidate
  6. Rough Road:    accel_z_std > 0.12
                    AND 0.35 <= accel_z_peak_to_peak <= 1.50
                   -> label: rough_road_candidate

Gate 3 — Default Baseline:
  7. Otherwise:    label: normal

Strict Ground-Truth Isolation:
------------------------------
This module NEVER reads, references, or outputs ground-truth labels
(ground_truth_event, ground_truth_type). All decisions are strictly
derived from motion features.
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd

# Default project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"
OUTPUT_CANDIDATES_PATH = PROJECT_ROOT / "data" / "processed" / "candidate_events.csv"

# ─── Detection Threshold Constants ───────────────────────────────────────────
# Gate 1: Vehicle Dynamics
TURNING_GYRO_Z_MIN = 0.025      # rad/s — yaw rate threshold
TURNING_ACCEL_X_MIN = 0.30      # m/s²  — lateral acceleration threshold
BRAKING_ACCEL_Y_MAX = -0.50     # m/s²  — longitudinal deceleration threshold
ACCEL_ACCEL_Y_MIN = 0.25        # m/s²  — longitudinal acceleration threshold

# Gate 2: Road-Surface Anomalies
SPEED_BREAKER_P2P_MIN = 1.60    # m/s²  — large vertical arch displacement
POTHOLE_DIFF_MIN = 0.20         # m/s²  — sample-to-sample vertical jerk
POTHOLE_IMPULSE_RATIO_MIN = 4.0 # dimensionless — peak_to_peak / std crest factor
ROUGH_ROAD_STD_MIN = 0.12       # m/s²  — sustained vertical vibration variance
ROUGH_ROAD_P2P_MIN = 0.35       # m/s²  — lower bound for rough road peak-to-peak
ROUGH_ROAD_P2P_MAX = 1.50       # m/s²  — upper bound for rough road peak-to-peak

# Expected candidate type labels
VALID_CANDIDATE_TYPES = {
    "normal",
    "turning_candidate",
    "braking_candidate",
    "acceleration_candidate",
    "speed_breaker_candidate",
    "pothole_candidate",
    "rough_road_candidate",
}

# Required metadata columns to verify preservation
REQUIRED_METADATA_COLUMNS = [
    "pass_id",
    "window_start",
    "window_end",
    "window_duration",
    "gps_lat_start",
    "gps_lon_start",
    "gps_lat_end",
    "gps_lon_end",
    "gps_displacement",
]


def load_features(csv_path=INPUT_FEATURES_PATH):
    """
    Load feature dataset from CSV.

    Parameters
    ----------
    csv_path : str or Path
        Path to features CSV.

    Returns
    -------
    pd.DataFrame
        Loaded feature DataFrame.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Features file not found at: {path}")
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Features file is empty: {path}")
    return df


def classify_window(row):
    """
    Classify a single feature window using hierarchical gating rules.

    Parameters
    ----------
    row : pd.Series or dict-like
        A single row containing window feature values.

    Returns
    -------
    str
        Candidate type label.
    """
    # ─── Gate 1: Vehicle Dynamics ─────────────────────────────────────────────
    # 1. Turning: yaw rotational velocity combined with lateral force
    if (row["gyro_z_max_abs"] > TURNING_GYRO_Z_MIN and
            row["accel_x_max_abs"] > TURNING_ACCEL_X_MIN):
        return "turning_candidate"

    # 2. Braking: sustained forward deceleration
    if row["accel_y_mean"] < BRAKING_ACCEL_Y_MAX:
        return "braking_candidate"

    # 3. Acceleration: sustained forward acceleration
    if row["accel_y_mean"] > ACCEL_ACCEL_Y_MIN:
        return "acceleration_candidate"

    # ─── Gate 2: Road-Surface Candidates ──────────────────────────────────────
    # 4. Speed Breaker: broad vertical amplitude exceeding obstacle threshold
    if row["accel_z_peak_to_peak"] > SPEED_BREAKER_P2P_MIN:
        return "speed_breaker_candidate"

    # 5. Pothole: sharp sample-to-sample jerk with high impulsive crest ratio
    std_z = row["accel_z_std"]
    if std_z is not None and not np.isnan(std_z) and std_z > 1e-9:
        impulse_ratio = row["accel_z_peak_to_peak"] / std_z
    else:
        impulse_ratio = 0.0

    if row["accel_z_max_abs_diff"] > POTHOLE_DIFF_MIN and impulse_ratio > POTHOLE_IMPULSE_RATIO_MIN:
        return "pothole_candidate"

    # 6. Rough Road: sustained multi-cycle vibration with bounded peak-to-peak
    if (row["accel_z_std"] > ROUGH_ROAD_STD_MIN and
            ROUGH_ROAD_P2P_MIN <= row["accel_z_peak_to_peak"] <= ROUGH_ROAD_P2P_MAX):
        return "rough_road_candidate"

    # ─── Gate 3: Default Baseline ─────────────────────────────────────────────
    return "normal"


def detect_candidates(features_df):
    """
    Apply candidate detection across all windows in a feature DataFrame.

    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame of extracted window features.

    Returns
    -------
    pd.DataFrame
        DataFrame with preserved metadata, all features, plus candidate_type and candidate.
    """
    if features_df.empty:
        raise ValueError("Cannot run candidate detection on an empty DataFrame.")

    # Guard: Ground truth isolation
    forbidden_gt = [c for c in ["ground_truth_event", "ground_truth_type"] if c in features_df.columns]
    if forbidden_gt:
        raise ValueError(f"Ground truth columns found in feature input: {forbidden_gt}. Detector must not use ground truth.")

    # Validate required feature columns
    needed_features = [
        "gyro_z_max_abs",
        "accel_x_max_abs",
        "accel_y_mean",
        "accel_z_peak_to_peak",
        "accel_z_max_abs_diff",
        "accel_z_std",
    ]
    missing = set(needed_features) - set(features_df.columns)
    if missing:
        raise KeyError(f"Missing required feature columns for candidate detection: {missing}")

    # Classify each window
    candidate_types = features_df.apply(classify_window, axis=1)

    # Construct output DataFrame preserving all columns + candidate flags
    output_df = features_df.copy()
    output_df["candidate_type"] = candidate_types
    output_df["candidate"] = (output_df["candidate_type"] != "normal").astype(int)

    return output_df


def save_candidates(candidates_df, output_path=OUTPUT_CANDIDATES_PATH):
    """
    Save detected candidate events to CSV.

    Parameters
    ----------
    candidates_df : pd.DataFrame
        Candidate event DataFrame.
    output_path : str or Path
        Target CSV file path.

    Returns
    -------
    Path
        Absolute path to saved CSV.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    candidates_df.to_csv(path, index=False)
    return path


def run_pipeline(input_path=INPUT_FEATURES_PATH, output_path=OUTPUT_CANDIDATES_PATH):
    """
    Execute full candidate detection pipeline from input CSV to output CSV.

    Parameters
    ----------
    input_path : str or Path
        Path to features CSV.
    output_path : str or Path
        Path to output candidate events CSV.

    Returns
    -------
    pd.DataFrame
        Detected candidate DataFrame.
    """
    features_df = load_features(input_path)
    candidates_df = detect_candidates(features_df)
    save_candidates(candidates_df, output_path)
    return candidates_df


def main():
    """Command-line entry point."""
    print("\n==================================================")
    print("  ROADPULSE -- Candidate Event Detection")
    print("==================================================")
    print(f"  Input  : {INPUT_FEATURES_PATH}")
    print(f"  Output : {OUTPUT_CANDIDATES_PATH}")

    candidates_df = run_pipeline()

    print("\n  Detection Summary:")
    print("  ------------------")
    print(f"  Total Windows : {len(candidates_df):,}")
    print(f"  Candidates    : {int((candidates_df['candidate'] == 1).sum()):,}")
    print(f"  Normal        : {int((candidates_df['candidate'] == 0).sum()):,}")
    print("\n  Breakdown by Candidate Type:")
    counts = candidates_df["candidate_type"].value_counts()
    for ctype, cnt in counts.items():
        pct = (cnt / len(candidates_df)) * 100
        print(f"    - {ctype:<25}: {cnt:>4}  ({pct:>5.1f}%)")

    print("\n==================================================")
    print("  [PASS] Candidate detection completed successfully.")
    print("==================================================\n")


if __name__ == "__main__":
    main()
