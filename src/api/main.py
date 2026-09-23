"""
src/api/main.py

ROADPULSE Hackathon REST API
============================
A lightweight, read-only FastAPI service exposing road-condition sensing
pipeline results (scored road segments and map-matched anomaly events)
to the Next.js frontend dashboard.

Design Principles:
------------------
- Read-only: reads existing processed CSV pipeline outputs.
- Ground truth isolated: never exposes ground-truth labels to consumers.
- Frontend normalized: maps internal 'rough_road' naming to 'rough_patch'
  at the API boundary to match the frontend TypeScript contracts.
- Deterministic, explainable, lightweight.
"""

from pathlib import Path
import os
from typing import List, Dict, Any, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA_DIR = BASE_DIR / "data" / "processed"


def get_data_dir() -> Path:
    """Return directory path holding processed CSV artifacts."""
    env_dir = os.environ.get("ROADPULSE_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return DEFAULT_DATA_DIR


def get_scored_segments_path() -> Path:
    return get_data_dir() / "scored_segments.csv"


def get_map_matched_events_path() -> Path:
    return get_data_dir() / "map_matched_events.csv"


# ---------------------------------------------------------------------------
# FastAPI Application & CORS Setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ROADPULSE API",
    description="Read-only API layer serving processed road condition results to the Next.js dashboard.",
    version="1.0.0",
)

# Local Next.js development origins
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://roadpulse-ecru.vercel.app",
    "https://roadpulse-o41102c1x-route-254b.vercel.app",
]app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Data normalization helpers
# ---------------------------------------------------------------------------

def normalize_event_type(value: Optional[str]) -> Optional[str]:
    """
    Normalize backend event types to frontend nomenclature.
    Specifically: 'rough_road' -> 'rough_patch'.
    """
    if not isinstance(value, str):
        return value
    if value == "rough_road":
        return "rough_patch"
    return value


def normalize_observed_types(value: Optional[str]) -> Optional[str]:
    """Normalize comma-separated observed types for frontend display."""
    if not isinstance(value, str):
        return value
    tokens = [t.strip() for t in value.split(",")]
    normalized = [normalize_event_type(t) for t in tokens]
    return ",".join(normalized)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint indicating API operational status."""
    return {"status": "ok"}


@app.get("/segments")
def get_segments() -> List[Dict[str, Any]]:
    """
    Return scored road segments from data/processed/scored_segments.csv.

    Normalizes 'rough_road' -> 'rough_patch' for frontend compatibility while
    preserving all scoring attributes (severity, confidence, counts).
    """
    csv_path = get_scored_segments_path()
    if not csv_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Scored segments data file not found at: {csv_path}. Please run the pipeline first.",
        )

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read scored segments file: {str(e)}",
        )

    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        rough_road_cnt = int(row.get("rough_road_count", 0))
        pothole_cnt = int(row.get("pothole_count", 0))
        speed_breaker_cnt = int(row.get("speed_breaker_count", 0))
        total_cnt = int(row.get("total_event_count", 0))
        unique_passes = int(row.get("unique_pass_count", 0))

        raw_primary = str(row.get("primary_condition", ""))
        normalized_primary = normalize_event_type(raw_primary)

        raw_observed = str(row.get("event_types_observed", ""))
        normalized_observed = normalize_observed_types(raw_observed)

        road_seg_id = str(row.get("road_segment_id", ""))
        sev_score = float(row.get("severity_score", 0.0))
        conf_score = float(row.get("confidence_score", 0.0))
        conf_pct = float(row.get("confidence_percent", 0.0))

        record = {
            # Required core fields
            "road_segment_id": road_seg_id,
            "total_event_count": total_cnt,
            "unique_pass_count": unique_passes,
            "pothole_count": pothole_cnt,
            "speed_breaker_count": speed_breaker_cnt,
            "rough_road_count": rough_road_cnt,
            "rough_patch_count": rough_road_cnt,  # Frontend convenience alias
            "severity_score": sev_score,
            "severity_label": str(row.get("severity_label", "")),
            "confidence_score": conf_score,
            "confidence_percent": conf_pct,
            "confidence_label": str(row.get("confidence_label", "")),
            "primary_condition": normalized_primary,

            # Additional pipeline scoring context
            "pass_ids": str(row.get("pass_ids", "")),
            "event_types_observed": normalized_observed,
            "raw_severity": float(row.get("raw_severity", 0.0)),

            # Frontend TypeScript RoadSegment model compatibility aliases
            "id": road_seg_id,
            "name": road_seg_id.replace("_", " ").title(),
            "conditionScore": round(max(0.0, 100.0 - sev_score), 2),
            "eventCount": total_cnt,
            "potholeCount": pothole_cnt,
            "speedBreakerCount": speed_breaker_cnt,
            "roughPatchCount": rough_road_cnt,
            "busPasses": unique_passes,
            "confidence": conf_score,
        }
        records.append(record)

    # Deterministic sort by segment ID
    records.sort(key=lambda r: r["road_segment_id"])
    return records


@app.get("/events")
def get_events() -> List[Dict[str, Any]]:
    """
    Return detected road anomaly events from data/processed/map_matched_events.csv.

    Normalizes 'rough_road' -> 'rough_patch' and strictly excludes any
    ground-truth fields from API responses.
    """
    csv_path = get_map_matched_events_path()
    if not csv_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Map matched events data file not found at: {csv_path}. Please run the pipeline first.",
        )

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read map matched events file: {str(e)}",
        )

    # Strictly filter out any ground-truth columns if present
    forbidden_prefixes = ("ground_truth", "gt_")
    safe_columns = [col for col in df.columns if not any(col.startswith(p) for p in forbidden_prefixes)]
    filtered_df = df[safe_columns]

    records: List[Dict[str, Any]] = []
    for _, row in filtered_df.iterrows():
        raw_type = str(row.get("event_type", ""))
        normalized_type = normalize_event_type(raw_type)

        center_lat = float(row.get("center_latitude", 0.0))
        center_lon = float(row.get("center_longitude", 0.0))
        match_lat = float(row.get("map_match_latitude", center_lat))
        match_lon = float(row.get("map_match_longitude", center_lon))

        record = {
            # Required core fields
            "event_id": str(row.get("event_id", "")),
            "pass_id": int(row.get("pass_id", 0)),
            "event_type": normalized_type,
            "start_time": float(row.get("start_time", 0.0)),
            "end_time": float(row.get("end_time", 0.0)),
            "duration": float(row.get("duration", 0.0)),
            "center_latitude": center_lat,
            "center_longitude": center_lon,
            "map_match_latitude": match_lat,
            "map_match_longitude": match_lon,
            "road_segment_id": str(row.get("road_segment_id", "")),
            "map_match_status": str(row.get("map_match_status", "")),

            # Metadata
            "window_count": int(row.get("window_count", 0)),
            "gps_valid": int(row.get("gps_valid", 1)),
            "inside_route_area": int(row.get("inside_route_area", 1)),
            "gps_quality": str(row.get("gps_quality", "")),
            "map_match_distance_m": float(row.get("map_match_distance_m", 0.0)),

            # Frontend TypeScript RoadEvent model compatibility aliases
            "id": str(row.get("event_id", "")),
            "eventType": normalized_type,
            "latitude": match_lat,
            "longitude": match_lon,
            "segmentId": str(row.get("road_segment_id", "")),
        }
        records.append(record)

    # Deterministic sort by pass_id and start_time
    records.sort(key=lambda r: (r["pass_id"], r["start_time"], r["event_id"]))
    return records

