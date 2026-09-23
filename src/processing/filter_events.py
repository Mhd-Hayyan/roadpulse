"""
ROADPULSE — Temporal / Context Event Filtering (Milestone 8)
===========================================================
Converts window-level classified road anomaly detections into physical
event-level detections through temporal clustering and context-aware boundary absorption.

Pipeline Architecture:
----------------------
1. Road Event Isolation:
   - Evaluates only genuine road-surface anomaly types:
     {'pothole', 'speed_breaker', 'rough_road'}
   - Excludes non-road vehicle dynamics and normal driving:
     {'normal', 'turning', 'braking', 'acceleration'}

2. Pass Independence:
   - Processes each pass_id independently so events never cross pass boundaries.

3. Same-Type Temporal Consolidation:
   - Sorts road-event windows chronologically by window_start.
   - Merges same-type windows that overlap or are adjacent:
     next.window_start <= current_cluster_end + 0.30 seconds
   - Consolidates them into a single physical road event.

4. Speed-Breaker Boundary Context Absorption:
   - If a speed_breaker cluster has immediately adjacent, short rough_road windows
     before or after it (representing ramp/boundary chassis rattle during hump traversal),
     those boundary rough_road windows are absorbed into the speed_breaker event.
   - Sustained rough_road sections (multi-second stretches) and potholes are
     strictly preserved as separate physical events.

5. Physical Event Record:
   - event_id: Unique sequential identifier (e.g., 'evt_001')
   - pass_id: Identifier of the bus pass
   - event_type: Consolidated physical event type
   - start_time: Physical event onset time (seconds)
   - end_time: Physical event completion time (seconds)
   - duration: Consolidated event duration (seconds)
   - center_latitude: Mean latitude across all windows in cluster
   - center_longitude: Mean longitude across all windows in cluster
   - window_count: Total number of constituent sensor windows

Strict Isolation:
-----------------
Ground truth is never read, referenced, or outputted by this module.
Multi-pass aggregation, map matching, and severity/confidence scoring are deferred.
"""

from pathlib import Path
import numpy as np
import pandas as pd

# Default project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_CLASSIFIED_PATH = PROJECT_ROOT / "data" / "processed" / "classified_events.csv"
OUTPUT_FILTERED_PATH = PROJECT_ROOT / "data" / "processed" / "filtered_events.csv"

# Permitted road-surface event types
ROAD_EVENT_TYPES = {"pothole", "speed_breaker", "rough_road"}

# Temporal clustering parameters
ADJACENCY_THRESHOLD = 0.30           # seconds — max gap between adjacent windows to merge
MAX_BOUNDARY_ROUGH_WINDOWS = 4      # max windows for local boundary roughness near speed breaker
MAX_BOUNDARY_ROUGH_DURATION = 1.80  # seconds — max duration for local boundary roughness

# Required output schema
REQUIRED_OUTPUT_COLUMNS = [
    "event_id",
    "pass_id",
    "event_type",
    "start_time",
    "end_time",
    "duration",
    "center_latitude",
    "center_longitude",
    "window_count",
]


def load_classified_events(csv_path=INPUT_CLASSIFIED_PATH):
    """
    Load classified events from CSV.

    Parameters
    ----------
    csv_path : str or Path
        Path to classified events CSV.

    Returns
    -------
    pd.DataFrame
        Loaded classified events DataFrame.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Classified events file not found at: {path}")
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Classified events file is empty: {path}")
    return df


def filter_road_events(classified_df):
    """
    Filter classified windows to retain only valid road-surface events.

    Parameters
    ----------
    classified_df : pd.DataFrame
        Window-level classified events DataFrame.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame containing only pothole, speed_breaker, or rough_road windows.
    """
    # Guard: Ground truth isolation
    forbidden_gt = [c for c in ["ground_truth_event", "ground_truth_type"] if c in classified_df.columns]
    if forbidden_gt:
        raise ValueError(f"Ground truth columns found in classified input: {forbidden_gt}. Filter must not use ground truth.")

    if "event_type" not in classified_df.columns:
        raise KeyError("Missing required column 'event_type' in classified input.")

    road_mask = classified_df["event_type"].isin(ROAD_EVENT_TYPES)
    return classified_df[road_mask].copy()


def cluster_same_type_windows(road_df_pass):
    """
    Merge temporally overlapping or adjacent windows of the same event type within a single pass.

    Parameters
    ----------
    road_df_pass : pd.DataFrame
        Road event windows for a single bus pass, sorted chronologically.

    Returns
    -------
    list[dict]
        List of cluster dictionaries.
    """
    if road_df_pass.empty:
        return []

    sorted_df = road_df_pass.sort_values("window_start")
    clusters = []
    curr = None

    for _, row in sorted_df.iterrows():
        if curr is None:
            curr = {
                "event_type": row["event_type"],
                "start_time": float(row["window_start"]),
                "end_time": float(row["window_end"]),
                "windows": [row],
            }
        elif (row["event_type"] == curr["event_type"] and
                float(row["window_start"]) <= curr["end_time"] + ADJACENCY_THRESHOLD):
            curr["end_time"] = max(curr["end_time"], float(row["window_end"]))
            curr["windows"].append(row)
        else:
            clusters.append(curr)
            curr = {
                "event_type": row["event_type"],
                "start_time": float(row["window_start"]),
                "end_time": float(row["window_end"]),
                "windows": [row],
            }

    if curr is not None:
        clusters.append(curr)

    return clusters


def absorb_speed_breaker_boundaries(clusters):
    """
    Absorb immediately adjacent, short boundary rough_road clusters into speed_breaker events.

    Parameters
    ----------
    clusters : list[dict]
        Chronologically ordered initial clusters for a single pass.

    Returns
    -------
    list[dict]
        Refined cluster list with speed-breaker boundary roughness absorbed.
    """
    if not clusters:
        return []

    absorbed_indices = set()
    result = []

    for i, cluster in enumerate(clusters):
        if i in absorbed_indices:
            continue

        if cluster["event_type"] == "speed_breaker":
            sb_cluster = {
                "event_type": "speed_breaker",
                "start_time": cluster["start_time"],
                "end_time": cluster["end_time"],
                "windows": list(cluster["windows"]),
            }

            # Check preceding cluster (boundary rattle on approach ramp)
            if i > 0 and (i - 1) not in absorbed_indices:
                prev_c = clusters[i - 1]
                if (prev_c["event_type"] == "rough_road" and
                        len(prev_c["windows"]) <= MAX_BOUNDARY_ROUGH_WINDOWS and
                        (prev_c["end_time"] - prev_c["start_time"]) <= MAX_BOUNDARY_ROUGH_DURATION and
                        sb_cluster["start_time"] <= prev_c["end_time"] + ADJACENCY_THRESHOLD):
                    if result and result[-1] is prev_c:
                        result.pop()
                    sb_cluster["start_time"] = min(sb_cluster["start_time"], prev_c["start_time"])
                    sb_cluster["end_time"] = max(sb_cluster["end_time"], prev_c["end_time"])
                    sb_cluster["windows"] = list(prev_c["windows"]) + sb_cluster["windows"]
                    absorbed_indices.add(i - 1)

            # Check succeeding cluster (boundary rattle on departure ramp)
            if i + 1 < len(clusters):
                next_c = clusters[i + 1]
                if (next_c["event_type"] == "rough_road" and
                        len(next_c["windows"]) <= MAX_BOUNDARY_ROUGH_WINDOWS and
                        (next_c["end_time"] - next_c["start_time"]) <= MAX_BOUNDARY_ROUGH_DURATION and
                        next_c["start_time"] <= sb_cluster["end_time"] + ADJACENCY_THRESHOLD):
                    sb_cluster["start_time"] = min(sb_cluster["start_time"], next_c["start_time"])
                    sb_cluster["end_time"] = max(sb_cluster["end_time"], next_c["end_time"])
                    sb_cluster["windows"] = sb_cluster["windows"] + list(next_c["windows"])
                    absorbed_indices.add(i + 1)

            result.append(sb_cluster)
        else:
            result.append(cluster)

    return result


def compute_event_center_gps(windows):
    """
    Calculate mean center GPS coordinates across all constituent windows in a cluster.

    Parameters
    ----------
    windows : list
        List of constituent window Series or dicts containing GPS coordinates.

    Returns
    -------
    tuple[float, float]
        (center_latitude, center_longitude) rounded to 6 decimal places.
    """
    lats = []
    lons = []

    for w in windows:
        if "gps_lat_start" in w and not pd.isna(w["gps_lat_start"]):
            lats.append(float(w["gps_lat_start"]))
        if "gps_lat_end" in w and not pd.isna(w["gps_lat_end"]):
            lats.append(float(w["gps_lat_end"]))
        if "gps_lon_start" in w and not pd.isna(w["gps_lon_start"]):
            lons.append(float(w["gps_lon_start"]))
        if "gps_lon_end" in w and not pd.isna(w["gps_lon_end"]):
            lons.append(float(w["gps_lon_end"]))

    if not lats or not lons:
        raise ValueError("Cannot calculate center GPS: missing GPS coordinates in windows.")

    center_lat = round(float(np.mean(lats)), 6)
    center_lon = round(float(np.mean(lons)), 6)
    return center_lat, center_lon


def filter_and_consolidate_events(classified_df):
    """
    Consolidate classified window events into physical road events.

    Parameters
    ----------
    classified_df : pd.DataFrame
        Window-level classified events DataFrame.

    Returns
    -------
    pd.DataFrame
        Consolidated physical event DataFrame matching REQUIRED_OUTPUT_COLUMNS.
    """
    road_df = filter_road_events(classified_df)
    if road_df.empty:
        return pd.DataFrame(columns=REQUIRED_OUTPUT_COLUMNS)

    consolidated_events = []
    event_counter = 1

    # Process each bus pass independently in sorted order
    for pid in sorted(road_df["pass_id"].unique()):
        p_df = road_df[road_df["pass_id"] == pid]

        # 1. Cluster same-type overlapping/adjacent windows
        initial_clusters = cluster_same_type_windows(p_df)

        # 2. Absorb boundary rough road into speed breaker events
        refined_clusters = absorb_speed_breaker_boundaries(initial_clusters)

        # 3. Formulate physical event records
        for cluster in refined_clusters:
            start_t = round(float(cluster["start_time"]), 2)
            end_t = round(float(cluster["end_time"]), 2)
            duration = round(end_t - start_t, 2)
            center_lat, center_lon = compute_event_center_gps(cluster["windows"])
            wcount = len(cluster["windows"])

            consolidated_events.append({
                "event_id": f"evt_{event_counter:03d}",
                "pass_id": int(pid),
                "event_type": cluster["event_type"],
                "start_time": start_t,
                "end_time": end_t,
                "duration": duration,
                "center_latitude": center_lat,
                "center_longitude": center_lon,
                "window_count": wcount,
            })
            event_counter += 1

    return pd.DataFrame(consolidated_events, columns=REQUIRED_OUTPUT_COLUMNS)


def save_filtered_events(filtered_df, output_path=OUTPUT_FILTERED_PATH):
    """
    Save consolidated physical events to CSV.

    Parameters
    ----------
    filtered_df : pd.DataFrame
        Physical event DataFrame.
    output_path : str or Path
        Target CSV file path.

    Returns
    -------
    Path
        Absolute path to saved CSV.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    filtered_df.to_csv(path, index=False)
    return path


def run_pipeline(input_path=INPUT_CLASSIFIED_PATH, output_path=OUTPUT_FILTERED_PATH):
    """
    Execute full event filtering pipeline from classified CSV to filtered physical events CSV.

    Parameters
    ----------
    input_path : str or Path
        Path to classified events CSV.
    output_path : str or Path
        Path to output filtered events CSV.

    Returns
    -------
    pd.DataFrame
        Consolidated physical event DataFrame.
    """
    classified_df = load_classified_events(input_path)
    filtered_df = filter_and_consolidate_events(classified_df)
    save_filtered_events(filtered_df, output_path)
    return filtered_df


def main():
    """Command-line entry point."""
    print("\n==================================================")
    print("  ROADPULSE -- Temporal Event Filtering (Milestone 8)")
    print("==================================================")
    print(f"  Input  : {INPUT_CLASSIFIED_PATH}")
    print(f"  Output : {OUTPUT_FILTERED_PATH}")

    filtered_df = run_pipeline()

    print("\n  Consolidation Summary:")
    print("  ----------------------")
    print(f"  Physical Road Events : {len(filtered_df)}")
    print(f"  Passes Represented   : {filtered_df['pass_id'].nunique()}")

    print("\n  Breakdown by Physical Event Type:")
    counts = filtered_df["event_type"].value_counts()
    for etype, cnt in counts.items():
        pct = (cnt / len(filtered_df)) * 100
        print(f"    - {etype:<20}: {cnt:>3}  ({pct:>5.1f}%)")

    print("\n  Event Details by Pass:")
    for pid in sorted(filtered_df["pass_id"].unique()):
        p_events = filtered_df[filtered_df["pass_id"] == pid]
        print(f"    Pass {pid} ({len(p_events)} events):")
        for _, r in p_events.iterrows():
            print(f"      [{r['event_id']}] {r['event_type']:<15} {r['start_time']:>6.2f}s - {r['end_time']:>6.2f}s ({r['duration']:>4.2f}s, {r['window_count']:>2} win) @ ({r['center_latitude']:.4f}, {r['center_longitude']:.4f})")

    print("\n==================================================")
    print("  [PASS] Temporal event filtering completed successfully.")
    print("==================================================\n")


if __name__ == "__main__":
    main()
