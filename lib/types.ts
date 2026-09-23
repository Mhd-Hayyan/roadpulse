/**
 * lib/types.ts
 *
 * Core TypeScript definitions for RoadPulse.
 *
 * Aligned with the backend API schema (src/api/) to ensure seamless
 * integration between frontend components and backend services.
 */

// ---------------------------------------------------------------------------
// Supported Event Types
// ---------------------------------------------------------------------------

export type EventType = "pothole" | "speed_breaker" | "rough_patch";

// ---------------------------------------------------------------------------
// RoadEvent
// ---------------------------------------------------------------------------

/**
 * Represents a single detected road anomaly event.
 * Matches backend JSON structure exactly.
 */
export interface RoadEvent {
  /** Unique event identifier, e.g., "evt_001" */
  event_id: string;

  /** Anomaly classification: pothole, speed_breaker, or rough_patch */
  event_type: EventType;

  /** GPS latitude coordinate */
  latitude: number;

  /** GPS longitude coordinate */
  longitude: number;

  /** Raw center latitude coordinate */
  center_latitude?: number;

  /** Raw center longitude coordinate */
  center_longitude?: number;

  /** Map-matched latitude coordinate */
  map_match_latitude?: number;

  /** Map-matched longitude coordinate */
  map_match_longitude?: number;

  /** Identifier of the road segment containing this event, e.g., "segment_015" */
  road_segment_id: string;

  /** Bus pass identifier for this event */
  pass_id?: number;

  /** Event duration in seconds */
  duration?: number;

  /** Event start timestamp in seconds */
  start_time?: number;

  /** Event end timestamp in seconds */
  end_time?: number;

  /** Geospatial map matching status, e.g. "matched" */
  map_match_status?: string;

  /** GPS quality flag */
  gps_quality?: string;

  /** Optional event-level rating if provided (do NOT fabricate if absent) */
  severity?: number;

  /** Optional event-level confidence score if provided (do NOT fabricate if absent) */
  confidence?: number;

  /** Number of independent bus passes confirming this anomaly */
  pass_count?: number;

  // Optional alias fields for UI component convenience
  id?: string;
  eventType?: EventType;
  segmentId?: string;
  busPasses?: number;
}

// ---------------------------------------------------------------------------
// RoadSegment
// ---------------------------------------------------------------------------

/**
 * Aggregated summary of a specific road segment's condition.
 */
export interface RoadSegment {
  /** Unique segment identifier, e.g., "segment_014" */
  id: string;

  /** Segment name or corridor description, e.g., "Kaloor - Edappally Road" */
  name: string;

  /**
   * Overall road health score.
   * Scale: 0 (critical damage) → 100 (perfect condition).
   */
  conditionScore: number;

  /** Total number of anomaly events detected on this segment */
  eventCount: number;

  /** Breakdown of pothole occurrences */
  potholeCount: number;

  /** Breakdown of speed breaker occurrences */
  speedBreakerCount: number;

  /** Breakdown of rough patch occurrences */
  roughPatchCount: number;

  /** Total bus passes across all monitoring vehicles on this segment */
  busPasses: number;

  /** Aggregated confidence score for this segment (0.0 - 1.0) */
  confidence: number;

  // Backend pipeline scoring fields
  road_segment_id?: string;
  total_event_count?: number;
  unique_pass_count?: number;
  pothole_count?: number;
  speed_breaker_count?: number;
  rough_road_count?: number;
  rough_patch_count?: number;
  severity_score?: number;
  severity_label?: string;
  confidence_score?: number;
  confidence_percent?: number;
  confidence_label?: string;
  primary_condition?: string;
  pass_ids?: string;
  event_types_observed?: string;
  raw_severity?: number;
}
