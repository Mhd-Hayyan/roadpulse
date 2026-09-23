"""
M10: Multi-Pass Aggregation
============================
Groups physical road events (one per bus pass per detection) by road segment
to produce a segment-level summary table.

The central question is:
    "How many DIFFERENT bus passes observed a road-condition event on this segment?"

Key design decisions
---------------------
- One physical event (from M8) = one observation.
- M8 already consolidated multiple sensor windows into physical events, so there
  is no double-counting of windows here.
- unique_pass_count counts DISTINCT pass_id values, NOT raw event rows.
  (A bus pass that detected a pothole AND a speed breaker on the same segment
   still counts as ONE pass for that segment.)
- Only events with map_match_status == "matched" are counted as valid observations.
  Events that failed GPS validation or fell outside the route are excluded.
- Ground-truth columns (ground_truth_event, ground_truth_type) are never used.
- All outputs are deterministic (sorted keys, sorted lists).
"""

import os
import argparse
import pandas as pd

# ---------------------------------------------------------------------------
# Road event types recognised by this pipeline
# ---------------------------------------------------------------------------
ROAD_EVENT_TYPES = ("pothole", "speed_breaker", "rough_road")

# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------

def aggregate_segments(df):
    """
    Aggregate map-matched road events by road segment.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns:
        event_id, pass_id, event_type, road_segment_id, map_match_status

    Returns
    -------
    pd.DataFrame
        One row per unique road_segment_id with summary statistics.
    """
    # Only count valid matched events
    valid = df[df["map_match_status"] == "matched"].copy()

    if valid.empty:
        return pd.DataFrame(columns=[
            "road_segment_id",
            "total_event_count",
            "unique_pass_count",
            "pothole_count",
            "speed_breaker_count",
            "rough_road_count",
            "pass_ids",
            "event_types_observed",
        ])

    rows = []
    for seg_id, group in valid.groupby("road_segment_id", sort=True):
        total_event_count = len(group)

        # Distinct bus passes – each pass counted once regardless of how many
        # events it contributed to this segment.
        unique_pass_ids   = sorted(group["pass_id"].unique())
        unique_pass_count = len(unique_pass_ids)

        # Per-type counts
        type_counts = group["event_type"].value_counts()
        pothole_count       = int(type_counts.get("pothole",       0))
        speed_breaker_count = int(type_counts.get("speed_breaker", 0))
        rough_road_count    = int(type_counts.get("rough_road",    0))

        # Deterministic string representations
        pass_ids_str = ",".join(str(p) for p in unique_pass_ids)

        observed_types = sorted(group["event_type"].unique())
        event_types_str = ",".join(observed_types)

        rows.append({
            "road_segment_id":      seg_id,
            "total_event_count":    total_event_count,
            "unique_pass_count":    unique_pass_count,
            "pothole_count":        pothole_count,
            "speed_breaker_count":  speed_breaker_count,
            "rough_road_count":     rough_road_count,
            "pass_ids":             pass_ids_str,
            "event_types_observed": event_types_str,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_map_matched_events(filepath="data/processed/map_matched_events.csv"):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found: {filepath}")
    return pd.read_csv(filepath)


def save_aggregated_segments(df, filepath="data/processed/aggregated_segments.csv"):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"Saved {len(df)} segment rows to {filepath}")


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(
    input_path  = "data/processed/map_matched_events.csv",
    output_path = "data/processed/aggregated_segments.csv",
):
    print("Running Milestone 10: Multi-Pass Aggregation...")
    df = load_map_matched_events(input_path)
    print(f"Loaded {len(df)} map-matched events.")

    n_valid   = (df["map_match_status"] == "matched").sum()
    n_invalid = len(df) - n_valid
    print(f"Valid (matched) events : {n_valid}")
    if n_invalid:
        print(f"Excluded (invalid/outside): {n_invalid}")

    agg = aggregate_segments(df)

    print(f"\nUnique road segments   : {len(agg)}")
    print(f"Total events aggregated: {agg['total_event_count'].sum()}")
    print()
    print(f"{'Segment':<18} {'Events':>7} {'Passes':>7} {'Potholes':>9} "
          f"{'SpBrk':>7} {'Rough':>7}  Pass IDs")
    print("-" * 80)
    for _, row in agg.iterrows():
        print(
            f"{row['road_segment_id']:<18} "
            f"{row['total_event_count']:>7} "
            f"{row['unique_pass_count']:>7} "
            f"{row['pothole_count']:>9} "
            f"{row['speed_breaker_count']:>7} "
            f"{row['rough_road_count']:>7}  "
            f"{row['pass_ids']}"
        )

    save_aggregated_segments(agg, output_path)
    return agg


def main():
    parser = argparse.ArgumentParser(
        description="M10: Aggregate road events across bus passes by road segment."
    )
    parser.add_argument(
        "--input",
        default="data/processed/map_matched_events.csv",
        help="Path to map-matched events CSV",
    )
    parser.add_argument(
        "--output",
        default="data/processed/aggregated_segments.csv",
        help="Path to output aggregated segments CSV",
    )
    args = parser.parse_args()
    run_pipeline(args.input, args.output)


if __name__ == "__main__":
    main()
