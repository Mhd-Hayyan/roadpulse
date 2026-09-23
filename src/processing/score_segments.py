"""
M11: Severity + Confidence Scoring
====================================
Assigns each aggregated road segment two independent scores:

    severity_score   -- how serious the road condition is, based on event
                        types and their weighted impact.
    confidence_score -- how consistently the condition was observed across
                        independent bus passes (repeat-observation coverage).

Design principle
----------------
Severity and confidence are deliberately SEPARATE.

    Severity answers:  "How bad is it?"
    Confidence answers: "How sure are we?"

A segment detected by only one pass may have very high severity (a deep
pothole) but low confidence (only one observation).  A segment seen on all
four passes with minor roughness has high confidence but low severity.
Conflating the two would produce misleading scores.

These labels and thresholds are PROTOTYPE scoring categories only.
They are NOT engineering road-safety standards.

Constants
---------
TOTAL_PASSES       -- total number of bus passes in the dataset.
                      Update this when the mock dataset grows.
POTHOLE_WEIGHT     -- impact weight for pothole events.
SPEED_BREAKER_WEIGHT -- impact weight for speed-breaker events.
ROUGH_ROAD_WEIGHT  -- impact weight for rough-road events.
SEVERITY_CAP       -- denominator used to normalise raw severity to 0-100.
                      Set to the maximum plausible raw severity for the
                      prototype (4 potholes * weight 3 = 12).
"""

import os
import argparse
import pandas as pd

# ---------------------------------------------------------------------------
# Configurable constants
# ---------------------------------------------------------------------------

TOTAL_PASSES = 4          # Total bus passes in the mock dataset

POTHOLE_WEIGHT       = 3  # Potholes are the most damaging event type
SPEED_BREAKER_WEIGHT = 1  # Speed breakers are engineered features, less severe
ROUGH_ROAD_WEIGHT    = 2  # Rough road is moderately severe

SEVERITY_CAP = 12         # max plausible raw severity: 4 potholes × 3 = 12
                          # keeps severity_score in [0, 100]

# Confidence label thresholds (inclusive lower bound)
CONF_VERY_HIGH = 0.75
CONF_HIGH      = 0.50
CONF_MODERATE  = 0.25
# below CONF_MODERATE -> "low"

# Severity label thresholds (score is 0-100, inclusive lower bound)
SEV_CRITICAL = 75
SEV_HIGH     = 50
SEV_MODERATE = 25
# below SEV_MODERATE -> "low"

# Required input columns (from M10 output)
REQUIRED_COLUMNS = [
    "road_segment_id",
    "total_event_count",
    "unique_pass_count",
    "pothole_count",
    "speed_breaker_count",
    "rough_road_count",
]


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def compute_confidence(unique_pass_count, total_passes=TOTAL_PASSES):
    """
    Confidence score = unique_pass_count / total_passes.

    Represents the fraction of independent bus passes that observed a road
    event on this segment.  Raises ValueError if unique_pass_count exceeds
    total_passes (indicates misconfigured TOTAL_PASSES).
    """
    if unique_pass_count > total_passes:
        raise ValueError(
            f"unique_pass_count ({unique_pass_count}) > TOTAL_PASSES ({total_passes}). "
            "Update TOTAL_PASSES to match the actual number of bus passes."
        )
    return unique_pass_count / total_passes


def confidence_label(score):
    """Return a human-readable confidence label for a score in [0, 1]."""
    if score >= CONF_VERY_HIGH:
        return "very_high"
    if score >= CONF_HIGH:
        return "high"
    if score >= CONF_MODERATE:
        return "moderate"
    return "low"


def compute_raw_severity(pothole_count, speed_breaker_count, rough_road_count):
    """
    Raw severity = weighted sum of event-type counts.
    Does NOT use unique_pass_count.
    """
    return (
        pothole_count       * POTHOLE_WEIGHT
        + speed_breaker_count * SPEED_BREAKER_WEIGHT
        + rough_road_count    * ROUGH_ROAD_WEIGHT
    )


def compute_severity_score(raw_severity, cap=SEVERITY_CAP):
    """Normalise raw severity to a 0–100 scale using the configured cap."""
    return min(raw_severity / cap, 1.0) * 100


def severity_label(score):
    """Return a human-readable severity label for a score in [0, 100]."""
    if score >= SEV_CRITICAL:
        return "critical"
    if score >= SEV_HIGH:
        return "high"
    if score >= SEV_MODERATE:
        return "moderate"
    return "low"


def primary_condition(pothole_count, speed_breaker_count, rough_road_count, total_event_count):
    """
    Return the dominant road-condition type for the segment.

    Rules (deterministic):
      1. Highest event count wins.
      2. Tie-break priority: pothole > rough_road > speed_breaker
      3. If total_event_count == 0, return 'none'.
    """
    if total_event_count == 0:
        return "none"

    # Build (count, tie-break-priority) tuples; lower priority number = higher precedence
    candidates = [
        (pothole_count,       0, "pothole"),
        (rough_road_count,    1, "rough_road"),
        (speed_breaker_count, 2, "speed_breaker"),
    ]
    # Sort by count descending, then priority ascending (lower = preferred)
    best = sorted(candidates, key=lambda t: (-t[0], t[1]))[0]
    return best[2]


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def score_segments(df, total_passes=TOTAL_PASSES):
    """
    Compute severity and confidence scores for every row in df.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain all REQUIRED_COLUMNS (M10 aggregated_segments output).
    total_passes : int
        Total number of independent bus passes in the dataset.

    Returns
    -------
    pd.DataFrame
        Input columns preserved; new scoring columns appended.
        Rows sorted deterministically by road_segment_id.

    Raises
    ------
    ValueError  if a required column is missing.
    ValueError  if any unique_pass_count > total_passes.
    ValueError  if any row's event-type counts don't sum to total_event_count.
    """
    # --- validate required columns ---
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Input DataFrame is missing required columns: {missing}")

    # --- validate count consistency ---
    computed_totals = (
        df["pothole_count"]
        + df["speed_breaker_count"]
        + df["rough_road_count"]
    )
    bad = df[computed_totals != df["total_event_count"]]
    if not bad.empty:
        raise ValueError(
            f"Event-type counts do not sum to total_event_count for segment(s): "
            f"{list(bad['road_segment_id'])}"
        )

    # --- validate pass counts ---
    over = df[df["unique_pass_count"] > total_passes]
    if not over.empty:
        raise ValueError(
            f"unique_pass_count exceeds TOTAL_PASSES ({total_passes}) for "
            f"segment(s): {list(over['road_segment_id'])}. "
            "Update TOTAL_PASSES."
        )

    out = df.copy().sort_values("road_segment_id").reset_index(drop=True)

    raw_sev_vals     = []
    sev_score_vals   = []
    sev_label_vals   = []
    conf_score_vals  = []
    conf_pct_vals    = []
    conf_label_vals  = []
    primary_cond_vals = []

    for _, row in out.iterrows():
        raw_sev = compute_raw_severity(
            row["pothole_count"],
            row["speed_breaker_count"],
            row["rough_road_count"],
        )
        sev_sc  = compute_severity_score(raw_sev)
        conf_sc = compute_confidence(row["unique_pass_count"], total_passes)

        raw_sev_vals.append(raw_sev)
        sev_score_vals.append(round(sev_sc, 4))
        sev_label_vals.append(severity_label(sev_sc))
        conf_score_vals.append(round(conf_sc, 4))
        conf_pct_vals.append(round(conf_sc * 100, 4))
        conf_label_vals.append(confidence_label(conf_sc))
        primary_cond_vals.append(
            primary_condition(
                row["pothole_count"],
                row["speed_breaker_count"],
                row["rough_road_count"],
                row["total_event_count"],
            )
        )

    out["raw_severity"]      = raw_sev_vals
    out["severity_score"]    = sev_score_vals
    out["severity_label"]    = sev_label_vals
    out["confidence_score"]  = conf_score_vals
    out["confidence_percent"] = conf_pct_vals
    out["confidence_label"]  = conf_label_vals
    out["primary_condition"] = primary_cond_vals

    return out


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_aggregated_segments(filepath="data/processed/aggregated_segments.csv"):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found: {filepath}")
    return pd.read_csv(filepath)


def save_scored_segments(df, filepath="data/processed/scored_segments.csv"):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"Saved {len(df)} scored segment rows to {filepath}")


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(
    input_path  = "data/processed/aggregated_segments.csv",
    output_path = "data/processed/scored_segments.csv",
    total_passes = TOTAL_PASSES,
):
    print("Running Milestone 11: Severity + Confidence Scoring...")
    df = load_aggregated_segments(input_path)
    print(f"Loaded {len(df)} aggregated segments  (TOTAL_PASSES={total_passes})")

    scored = score_segments(df, total_passes=total_passes)

    header = (
        f"{'Segment':<18} {'RawSev':>7} {'SevScr':>7} {'SevLbl':<10} "
        f"{'ConfScr':>8} {'Conf%':>6} {'ConfLbl':<10} {'Primary'}"
    )
    print()
    print(header)
    print("-" * len(header))
    for _, row in scored.iterrows():
        print(
            f"{row['road_segment_id']:<18} "
            f"{row['raw_severity']:>7} "
            f"{row['severity_score']:>7.1f} "
            f"{row['severity_label']:<10} "
            f"{row['confidence_score']:>8.2f} "
            f"{row['confidence_percent']:>6.1f} "
            f"{row['confidence_label']:<10} "
            f"{row['primary_condition']}"
        )

    print()
    print("Severity  distribution:",
          scored["severity_label"].value_counts().to_dict())
    print("Confidence distribution:",
          scored["confidence_label"].value_counts().to_dict())

    save_scored_segments(scored, output_path)
    return scored


def main():
    parser = argparse.ArgumentParser(
        description="M11: Score each road segment for severity and confidence."
    )
    parser.add_argument(
        "--input",  default="data/processed/aggregated_segments.csv",
        help="Path to aggregated segments CSV",
    )
    parser.add_argument(
        "--output", default="data/processed/scored_segments.csv",
        help="Path to output scored segments CSV",
    )
    parser.add_argument(
        "--total-passes", type=int, default=TOTAL_PASSES,
        dest="total_passes",
        help=f"Total number of bus passes in the dataset (default: {TOTAL_PASSES})",
    )
    args = parser.parse_args()
    run_pipeline(args.input, args.output, args.total_passes)


if __name__ == "__main__":
    main()
