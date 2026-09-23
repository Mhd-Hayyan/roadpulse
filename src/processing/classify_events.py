"""
ROADPULSE — Event Classification Pipeline (Milestone 7)
======================================================
Converts candidate detections into refined event classifications using
sensor-derived motion features.

Architecture & Scope:
---------------------
1. Vehicle Dynamics Isolation:
   - turning_candidate      -> turning      (is_road_event = 0)
   - braking_candidate      -> braking      (is_road_event = 0)
   - acceleration_candidate -> acceleration (is_road_event = 0)
   - normal                 -> normal       (is_road_event = 0)

2. Road-Surface Anomaly Refinement:
   - speed_breaker_candidate -> speed_breaker (is_road_event = 1)
     Refinement: If a high vertical amplitude window (>1.60 m/s²) exhibits violent
     sample-to-sample jerk (accel_z_max_abs_diff > 0.50) and a high crest factor
     (impulse_ratio > 4.5), it represents an intense pothole rebound rather than a
     smooth speed breaker arch, and is classified as 'pothole'.
   - pothole_candidate       -> pothole       (is_road_event = 1)
     Refinement: If elevated vertical variance is sustained (accel_z_std > 0.20)
     with moderate jerk (accel_z_max_abs_diff < 0.50) and a lower crest factor
     (impulse_ratio < 4.5), it represents continuous rough road chatter rather
     than an isolated strike, and is classified as 'rough_road'.
   - rough_road_candidate    -> rough_road    (is_road_event = 1)

3. Auxiliary Milestone 8 Field:
   - impulse_ratio: precalculated safe ratio (accel_z_peak_to_peak / accel_z_std)
     providing a standardized shock concentration metric for downstream
     false-positive filtering and severity scoring.

Strict Isolation:
-----------------
Ground truth is never read, referenced, or outputted by this module.
Temporal filtering (merging, window lookahead, map matching) is deferred to later milestones.
"""

from pathlib import Path
import numpy as np
import pandas as pd

# Default project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_CANDIDATES_PATH = PROJECT_ROOT / "data" / "processed" / "candidate_events.csv"
OUTPUT_CLASSIFIED_PATH = PROJECT_ROOT / "data" / "processed" / "classified_events.csv"

# Valid classified event types
VALID_EVENT_TYPES = {
    "normal",
    "turning",
    "braking",
    "acceleration",
    "pothole",
    "speed_breaker",
    "rough_road",
}

# Road event subset
ROAD_EVENT_TYPES = {"pothole", "speed_breaker", "rough_road"}

# Refinement thresholds
POTHOLE_REBOUND_DIFF_MIN = 0.50       # m/s² — sample-to-sample jerk threshold for severe pothole
POTHOLE_REBOUND_IMPULSE_MIN = 4.5     # crest factor threshold for severe pothole rebound
ROUGH_ROAD_CHATTER_STD_MIN = 0.20     # m/s² — sustained variance threshold for rough road chatter
ROUGH_ROAD_CHATTER_IMPULSE_MAX = 4.5  # crest factor upper bound for distributed road chatter


def load_candidate_events(csv_path=INPUT_CANDIDATES_PATH):
    """
    Load candidate events from CSV.

    Parameters
    ----------
    csv_path : str or Path
        Path to candidate events CSV.

    Returns
    -------
    pd.DataFrame
        Loaded candidate events DataFrame.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Candidate events file not found at: {path}")
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Candidate events file is empty: {path}")
    return df


def compute_impulse_ratio(peak_to_peak, std_z):
    """
    Safely calculate vertical impulse crest factor (peak_to_peak / std_z).

    Parameters
    ----------
    peak_to_peak : float
        Peak-to-peak vertical dynamic acceleration range (m/s²).
    std_z : float
        Vertical dynamic acceleration standard deviation (m/s²).

    Returns
    -------
    float
        Impulse ratio, or 0.0 if standard deviation is zero/invalid.
    """
    if std_z is not None and not np.isnan(std_z) and std_z > 1e-9:
        return float(peak_to_peak / std_z)
    return 0.0


def classify_event(row):
    """
    Classify a single candidate window into a refined event type.

    Parameters
    ----------
    row : pd.Series or dict-like
        A single row containing candidate and feature information.

    Returns
    -------
    str
        Refined event_type label.
    """
    ctype = row["candidate_type"]

    # 1. Vehicle dynamics candidates map directly (isolated in Gate 1 of 6B)
    if ctype == "turning_candidate":
        return "turning"
    if ctype == "braking_candidate":
        return "braking"
    if ctype == "acceleration_candidate":
        return "acceleration"
    if ctype == "normal":
        return "normal"

    # Derived physical feature: impulse ratio (crest factor)
    p2p = row["accel_z_peak_to_peak"]
    std_z = row["accel_z_std"]
    diff = row["accel_z_max_abs_diff"]
    impulse_ratio = compute_impulse_ratio(p2p, std_z)

    # 2. Speed breaker refinement:
    # A true speed breaker is a broad, smooth arch with moderate jerk (diff <= 0.50).
    # If high vertical displacement (>1.60 m/s²) exhibits violent sample-to-sample jerk (diff > 0.50)
    # and a sharp impulsive crest factor (>4.5), it represents an intense pothole rebound.
    if ctype == "speed_breaker_candidate":
        if diff > POTHOLE_REBOUND_DIFF_MIN and impulse_ratio > POTHOLE_REBOUND_IMPULSE_MIN:
            return "pothole"
        return "speed_breaker"

    # 3. Pothole refinement:
    # An isolated pothole strike has a high jerk-to-variance concentration.
    # If vertical variance is sustained (std_z > 0.20) with moderate jerk (diff < 0.50)
    # and a lower crest factor (<4.5), it represents continuous rough road chatter.
    if ctype == "pothole_candidate":
        if (std_z > ROUGH_ROAD_CHATTER_STD_MIN and
                impulse_ratio < ROUGH_ROAD_CHATTER_IMPULSE_MAX and
                diff < POTHOLE_REBOUND_DIFF_MIN):
            return "rough_road"
        return "pothole"

    # 4. Rough road candidate
    if ctype == "rough_road_candidate":
        return "rough_road"

    return "normal"


def classify_events(candidates_df):
    """
    Classify all candidate events in a DataFrame.

    Parameters
    ----------
    candidates_df : pd.DataFrame
        DataFrame of detected candidate events.

    Returns
    -------
    pd.DataFrame
        DataFrame with preserved input columns plus event_type, is_road_event, and impulse_ratio.
    """
    if candidates_df.empty:
        raise ValueError("Cannot classify an empty DataFrame.")

    # Guard: Ground truth isolation
    forbidden_gt = [c for c in ["ground_truth_event", "ground_truth_type"] if c in candidates_df.columns]
    if forbidden_gt:
        raise ValueError(f"Ground truth columns found in candidate input: {forbidden_gt}. Classifier must not use ground truth.")

    # Validate required input columns
    required_cols = [
        "candidate_type",
        "candidate",
        "accel_z_peak_to_peak",
        "accel_z_std",
        "accel_z_max_abs_diff",
    ]
    missing = set(required_cols) - set(candidates_df.columns)
    if missing:
        raise KeyError(f"Missing required columns for event classification: {missing}")

    # Compute classifications
    event_types = candidates_df.apply(classify_event, axis=1)

    # Compute precalculated impulse ratio for Milestone 8
    impulse_ratios = candidates_df.apply(
        lambda r: compute_impulse_ratio(r["accel_z_peak_to_peak"], r["accel_z_std"]),
        axis=1,
    )

    # Construct output DataFrame
    output_df = candidates_df.copy()
    output_df["event_type"] = event_types
    output_df["is_road_event"] = output_df["event_type"].isin(ROAD_EVENT_TYPES).astype(int)
    output_df["impulse_ratio"] = impulse_ratios.round(4)

    return output_df


def save_classified_events(classified_df, output_path=OUTPUT_CLASSIFIED_PATH):
    """
    Save classified events to CSV.

    Parameters
    ----------
    classified_df : pd.DataFrame
        Classified events DataFrame.
    output_path : str or Path
        Target CSV file path.

    Returns
    -------
    Path
        Absolute path to saved CSV.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    classified_df.to_csv(path, index=False)
    return path


def run_pipeline(input_path=INPUT_CANDIDATES_PATH, output_path=OUTPUT_CLASSIFIED_PATH):
    """
    Execute full event classification pipeline from candidate CSV to classified CSV.

    Parameters
    ----------
    input_path : str or Path
        Path to candidate events CSV.
    output_path : str or Path
        Path to classified events CSV.

    Returns
    -------
    pd.DataFrame
        Classified events DataFrame.
    """
    candidates_df = load_candidate_events(input_path)
    classified_df = classify_events(candidates_df)
    save_classified_events(classified_df, output_path)
    return classified_df


def main():
    """Command-line entry point."""
    print("\n==================================================")
    print("  ROADPULSE -- Event Classification (Milestone 7)")
    print("==================================================")
    print(f"  Input  : {INPUT_CANDIDATES_PATH}")
    print(f"  Output : {OUTPUT_CLASSIFIED_PATH}")

    classified_df = run_pipeline()

    print("\n  Classification Summary:")
    print("  -----------------------")
    print(f"  Total Windows : {len(classified_df):,}")
    print(f"  Road Events   : {int((classified_df['is_road_event'] == 1).sum()):,}")
    print(f"  Non-Road      : {int((classified_df['is_road_event'] == 0).sum()):,}")

    print("\n  Breakdown by Event Type:")
    counts = classified_df["event_type"].value_counts()
    for etype, cnt in counts.items():
        pct = (cnt / len(classified_df)) * 100
        is_road = "road" if etype in ROAD_EVENT_TYPES else "non-road"
        print(f"    - {etype:<20} ({is_road:>8}): {cnt:>4}  ({pct:>5.1f}%)")

    print("\n==================================================")
    print("  [PASS] Event classification completed successfully.")
    print("==================================================\n")


if __name__ == "__main__":
    main()
