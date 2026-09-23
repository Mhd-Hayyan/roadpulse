"""
tests/test_api.py

Test Suite for ROADPULSE REST API (Milestone 12)
=================================================
Validates endpoints, schema conformity, data normalization, ground truth
isolation, CORS configuration, and graceful missing-file error handling.
"""

import os
from fastapi.testclient import TestClient
import pytest

from src.api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health endpoint tests
# ---------------------------------------------------------------------------

def test_health_check_status_code_and_payload():
    """Verify GET /health returns 200 and status: ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


# ---------------------------------------------------------------------------
# Segments endpoint tests
# ---------------------------------------------------------------------------

def test_get_segments_status_and_non_empty():
    """Verify GET /segments returns 200 and a non-empty array."""
    response = client.get("/segments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_segments_required_fields_and_types():
    """Verify every segment contains all required fields with proper types."""
    response = client.get("/segments")
    assert response.status_code == 200
    segments = response.json()

    required_fields = [
        "road_segment_id",
        "total_event_count",
        "unique_pass_count",
        "pothole_count",
        "speed_breaker_count",
        "rough_road_count",
        "severity_score",
        "severity_label",
        "confidence_score",
        "confidence_percent",
        "confidence_label",
        "primary_condition",
    ]

    for segment in segments:
        for field in required_fields:
            assert field in segment, f"Missing required field '{field}' in segment {segment}"

        # Type validations
        assert isinstance(segment["road_segment_id"], str)
        assert isinstance(segment["total_event_count"], int)
        assert isinstance(segment["unique_pass_count"], int)
        assert isinstance(segment["pothole_count"], int)
        assert isinstance(segment["speed_breaker_count"], int)
        assert isinstance(segment["rough_road_count"], int)
        assert isinstance(segment["severity_score"], (int, float))
        assert isinstance(segment["severity_label"], str)
        assert isinstance(segment["confidence_score"], (int, float))
        assert isinstance(segment["confidence_percent"], (int, float))
        assert isinstance(segment["confidence_label"], str)
        assert isinstance(segment["primary_condition"], str)


def test_get_segments_rough_road_normalization():
    """
    Verify backend 'rough_road' is normalized to frontend 'rough_patch'
    at the API boundary (e.g. primary_condition and observed events).
    """
    response = client.get("/segments")
    assert response.status_code == 200
    segments = response.json()

    # Find segment_018 which is a rough road segment in the processed dataset
    seg_18 = next((s for s in segments if s["road_segment_id"] == "segment_018"), None)
    assert seg_18 is not None, "segment_018 should be present in scored segments"

    # Must be normalized to rough_patch
    assert seg_18["primary_condition"] == "rough_patch"
    assert "rough_road" not in seg_18["primary_condition"]
    assert "rough_patch" in seg_18["event_types_observed"]
    assert "rough_road" not in seg_18["event_types_observed"]

    # Also verify rough_patch_count alias is provided alongside rough_road_count
    assert "rough_patch_count" in seg_18
    assert seg_18["rough_patch_count"] == seg_18["rough_road_count"]
    assert seg_18["rough_patch_count"] > 0


def test_get_segments_no_ground_truth():
    """Verify GET /segments does not leak any ground-truth fields."""
    response = client.get("/segments")
    assert response.status_code == 200
    segments = response.json()

    for seg in segments:
        for key in seg.keys():
            assert not key.startswith("ground_truth"), f"Found ground truth field: {key}"
            assert not key.startswith("gt_"), f"Found gt prefix field: {key}"


def test_get_segments_deterministic_ordering():
    """Verify GET /segments is sorted deterministically by road_segment_id."""
    response = client.get("/segments")
    assert response.status_code == 200
    segments = response.json()
    segment_ids = [s["road_segment_id"] for s in segments]
    assert segment_ids == sorted(segment_ids)


# ---------------------------------------------------------------------------
# Events endpoint tests
# ---------------------------------------------------------------------------

def test_get_events_status_and_non_empty():
    """Verify GET /events returns 200 and a non-empty array."""
    response = client.get("/events")
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    assert len(events) > 0


def test_get_events_required_fields_and_types():
    """Verify every event contains all required fields with proper types."""
    response = client.get("/events")
    assert response.status_code == 200
    events = response.json()

    required_fields = [
        "event_id",
        "pass_id",
        "event_type",
        "start_time",
        "end_time",
        "duration",
        "center_latitude",
        "center_longitude",
        "map_match_latitude",
        "map_match_longitude",
        "road_segment_id",
        "map_match_status",
    ]

    for event in events:
        for field in required_fields:
            assert field in event, f"Missing required field '{field}' in event {event}"

        # Type validations
        assert isinstance(event["event_id"], str)
        assert isinstance(event["pass_id"], int)
        assert isinstance(event["event_type"], str)
        assert isinstance(event["start_time"], (int, float))
        assert isinstance(event["end_time"], (int, float))
        assert isinstance(event["duration"], (int, float))
        assert isinstance(event["center_latitude"], (int, float))
        assert isinstance(event["center_longitude"], (int, float))
        assert isinstance(event["map_match_latitude"], (int, float))
        assert isinstance(event["map_match_longitude"], (int, float))
        assert isinstance(event["road_segment_id"], str)
        assert isinstance(event["map_match_status"], str)


def test_get_events_strict_no_ground_truth():
    """Verify GET /events strictly excludes ground-truth fields."""
    response = client.get("/events")
    assert response.status_code == 200
    events = response.json()

    for event in events:
        for key in event.keys():
            assert not key.startswith("ground_truth"), f"Ground truth field leaked in event: {key}"
            assert not key.startswith("gt_"), f"Ground truth field leaked in event: {key}"
        assert "ground_truth_event" not in event
        assert "ground_truth_type" not in event


def test_get_events_rough_road_normalization():
    """
    Verify backend 'rough_road' events are normalized to 'rough_patch'
    in the API response for frontend compatibility.
    """
    response = client.get("/events")
    assert response.status_code == 200
    events = response.json()

    event_types = {e["event_type"] for e in events}
    # No event should ever have type 'rough_road'
    assert "rough_road" not in event_types, "'rough_road' must be normalized to 'rough_patch'"
    # 'rough_patch' should be present
    assert "rough_patch" in event_types, "'rough_patch' should exist among event types"

    # Specific event check (evt_004 is rough road in the raw/processed dataset)
    evt_4 = next((e for e in events if e["event_id"] == "evt_004"), None)
    assert evt_4 is not None
    assert evt_4["event_type"] == "rough_patch"


def test_get_events_deterministic_ordering():
    """Verify GET /events is sorted deterministically by (pass_id, start_time, event_id)."""
    response = client.get("/events")
    assert response.status_code == 200
    events = response.json()
    sort_keys = [(e["pass_id"], e["start_time"], e["event_id"]) for e in events]
    assert sort_keys == sorted(sort_keys)


# ---------------------------------------------------------------------------
# CORS configuration tests
# ---------------------------------------------------------------------------

def test_cors_headers_for_frontend():
    """Verify CORS headers allow requests from local Next.js frontend."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/segments", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


# ---------------------------------------------------------------------------
# Error handling tests (missing files)
# ---------------------------------------------------------------------------

def test_missing_data_files_raise_404(monkeypatch, tmp_path):
    """Verify clear 404 response is raised when processed CSV files are missing."""
    monkeypatch.setenv("ROADPULSE_DATA_DIR", str(tmp_path))

    segments_resp = client.get("/segments")
    assert segments_resp.status_code == 404
    assert "Scored segments data file not found" in segments_resp.json()["detail"]

    events_resp = client.get("/events")
    assert events_resp.status_code == 404
    assert "Map matched events data file not found" in events_resp.json()["detail"]
