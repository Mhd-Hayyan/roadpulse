"""
M9B: Offline Rule-Based Map Matching
=====================================
Assigns each validated road event to the nearest segment of our synthetic route.

Route Representation
--------------------
The synthetic bus route is a roughly NE-trending road through Ernakulam district
(Kerala, India).  It runs from approximately:
    lat 9.931, lon 76.267   (south-west start)
to  lat 9.941, lon 76.276   (north-east end)

We represent it as 8 ordered line segments (9 waypoints).  Each segment is defined
by two endpoint coordinates; the representative "anchor" point used for distance
calculation is the segment midpoint.

Waypoints were read from the preprocessed sensor CSV (column: latitude/longitude)
by sampling the route at evenly-spaced time intervals across one full pass so that
they honestly reflect the simulated GPS trace.

Segment naming starts at segment_014 to match the IDs given in the project spec.

Distance Calculation
--------------------
We use the Haversine formula to compute great-circle distance between two points
on a sphere.  For short urban distances (< 2 km) this is indistinguishable from
Euclidean distance projected on the local plane.

Matching Logic
--------------
For each event:
1.  Check gps_valid.  If 0 -> status = "invalid_gps".
2.  Check inside_route_area.  If 0 -> status = "outside_route".
3.  Otherwise compute Haversine distance from the event's map_match_latitude /
    map_match_longitude to every segment midpoint.
4.  Select the segment with the minimum distance.
5.  Record road_segment_id, map_match_distance_m, map_match_status = "matched".

Limitation
----------
We match to segment midpoints, not to the nearest point on each line segment.
This is an approximation; for a synthetic 60-second route with segments ~110-130 m
long the midpoint error is at most ~65 m and the correct segment is still selected
in practice.  A real-world deployment should use proper point-to-segment projection.
"""

import os
import math
import argparse
import pandas as pd

# ---------------------------------------------------------------------------
# Route definition
# ---------------------------------------------------------------------------
# Nine waypoints sampled from the preprocessed GPS trace (pass 1), spaced ~7 s
# apart to cover the 60-second route at roughly equal intervals.
# Each consecutive pair of waypoints defines one ROUTE_SEGMENT.

_WAYPOINTS = [
    (9.931224, 76.267341),   # t =  0 s  – route start
    (9.932196, 76.268269),   # t =  7 s
    (9.933127, 76.269031),   # t = 13 s
    (9.933933, 76.269930),   # t = 19 s
    (9.934876, 76.270525),   # t = 24 s
    (9.935832, 76.271186),   # t = 29 s
    (9.936887, 76.272099),   # t = 35 s
    (9.938196, 76.273365),   # t = 43 s
    (9.939411, 76.274218),   # t = 50 s
    (9.941079, 76.275699),   # t = 60 s  – route end
]

# Build the segment list from consecutive waypoint pairs.
# Segment IDs start at segment_014 as specified.
ROUTE_SEGMENTS = []
_START_ID = 14
for _i in range(len(_WAYPOINTS) - 1):
    seg_id = f"segment_{_START_ID + _i:03d}"
    start_pt = _WAYPOINTS[_i]
    end_pt   = _WAYPOINTS[_i + 1]
    mid_lat  = (start_pt[0] + end_pt[0]) / 2.0
    mid_lon  = (start_pt[1] + end_pt[1]) / 2.0
    ROUTE_SEGMENTS.append({
        "segment_id": seg_id,
        "start_lat":  start_pt[0],
        "start_lon":  start_pt[1],
        "end_lat":    end_pt[0],
        "end_lon":    end_pt[1],
        "mid_lat":    mid_lat,
        "mid_lon":    mid_lon,
    })


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Return the Haversine great-circle distance in metres between two points.
    Accurate to <0.1 % for distances up to a few hundred kilometres.
    """
    R = 6_371_000.0   # Earth mean radius in metres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def point_to_segment_distance(lat, lon, seg):
    """
    Approximate perpendicular distance from (lat, lon) to a route segment.

    Implementation note
    -------------------
    A true point-to-segment projection requires working in a local Cartesian
    coordinate system.  For the short distances involved in our prototype we
    use the midpoint of each segment as a representative anchor and compute
    Haversine distance to that point.  The maximum overestimate relative to
    the true perpendicular distance is at most half the segment length (~65 m)
    and does not affect which segment is selected as nearest for events that
    lie close to the route.
    """
    return haversine_distance(lat, lon, seg["mid_lat"], seg["mid_lon"])


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------

def match_event_to_segment(lat, lon, gps_valid, inside_route_area):
    """
    Return (road_segment_id, distance_m, status) for a single event.

    Parameters
    ----------
    lat, lon          : float  – map_match_latitude / map_match_longitude
    gps_valid         : int    – 1 if GPS coordinates are valid
    inside_route_area : int    – 1 if coordinates fall within the broad bbox

    Returns
    -------
    (segment_id: str | None, distance_m: float | None, status: str)
    """
    if not gps_valid:
        return None, None, "invalid_gps"
    if not inside_route_area:
        return None, None, "outside_route"

    best_seg  = None
    best_dist = float("inf")
    for seg in ROUTE_SEGMENTS:
        dist = point_to_segment_distance(lat, lon, seg)
        if dist < best_dist:
            best_dist = dist
            best_seg  = seg["segment_id"]

    return best_seg, best_dist, "matched"


def process_map_matching(df):
    """
    Apply map matching to every row of the GPS-processed events DataFrame.
    Adds three new columns:
        road_segment_id        – segment identifier (str or NaN)
        map_match_distance_m   – distance to segment midpoint in metres (float or NaN)
        map_match_status       – 'matched', 'invalid_gps', or 'outside_route'

    The function does NOT use ground_truth_event or ground_truth_type.
    """
    segment_ids = []
    distances   = []
    statuses    = []

    for _, row in df.iterrows():
        seg_id, dist, status = match_event_to_segment(
            lat               = row["map_match_latitude"],
            lon               = row["map_match_longitude"],
            gps_valid         = row["gps_valid"],
            inside_route_area = row["inside_route_area"],
        )
        segment_ids.append(seg_id)
        distances.append(dist)
        statuses.append(status)

    out = df.copy()
    out["road_segment_id"]      = segment_ids
    out["map_match_distance_m"] = distances
    out["map_match_status"]     = statuses
    return out


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_gps_processed_events(filepath="data/processed/gps_processed_events.csv"):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found: {filepath}")
    return pd.read_csv(filepath)


def save_map_matched_events(df, filepath="data/processed/map_matched_events.csv"):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"Saved {len(df)} map-matched events to {filepath}")


def run_pipeline(
    input_path  = "data/processed/gps_processed_events.csv",
    output_path = "data/processed/map_matched_events.csv",
):
    print("Running Milestone 9B: Map Matching...")
    df = load_gps_processed_events(input_path)
    print(f"Loaded {len(df)} GPS-processed events.")

    df_out = process_map_matching(df)

    n_matched = (df_out["map_match_status"] == "matched").sum()
    n_invalid = (df_out["map_match_status"] == "invalid_gps").sum()
    n_outside = (df_out["map_match_status"] == "outside_route").sum()

    print(f"Matched        : {n_matched}")
    print(f"Invalid GPS    : {n_invalid}")
    print(f"Outside route  : {n_outside}")

    matched = df_out[df_out["map_match_status"] == "matched"]["map_match_distance_m"]
    if len(matched) > 0:
        print(f"Distance (m)   : min={matched.min():.1f}, max={matched.max():.1f}, mean={matched.mean():.1f}")

    print("\nRoad segment distribution:")
    dist_table = (
        df_out[df_out["map_match_status"] == "matched"]
        .groupby("road_segment_id")
        .size()
        .reset_index(name="event_count")
    )
    for _, seg_row in dist_table.iterrows():
        print(f"  {seg_row['road_segment_id']}: {int(seg_row['event_count'])} event(s)")

    save_map_matched_events(df_out, output_path)
    return df_out


def main():
    parser = argparse.ArgumentParser(
        description="M9B: Offline map matching of filtered road events to route segments."
    )
    parser.add_argument(
        "--input",
        default="data/processed/gps_processed_events.csv",
        help="Path to GPS-processed events CSV",
    )
    parser.add_argument(
        "--output",
        default="data/processed/map_matched_events.csv",
        help="Path to output map-matched events CSV",
    )
    args = parser.parse_args()
    run_pipeline(args.input, args.output)


if __name__ == "__main__":
    main()
