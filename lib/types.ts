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

  /** Identifier of the road segment containing this event, e.g., "segment_014" */
  road_segment_id: string;

  /**
   * Anomaly severity rating.
   * Scale: 0 (very minor) → 100 (severe / critical).
   */
  severity: number;

  /**
   * Detection confidence score from signal processing.
   * Scale: 0.0 (low) → 1.0 (certain).
   */
  confidence: number;

  /**
   * Number of independent bus passes confirming this anomaly.
   */
  pass_count: number;

  // Optional alias fields for UI component convenience
  id?: string;
  eventType?: EventType;
  segmentId?: string;
  busPasses?: number;
}

// ---------------------------------------------------------------------------
// RoadSegmentGeometry (Backend API Shape)
// ---------------------------------------------------------------------------

/**
 * Shape of road segment geometry returned by the backend API.
 */
export interface RoadSegmentGeometry {
  road_segment_id: string;
  geometry: [number, number][];
  severity?: number;
  confidence?: number;
  pass_count?: number;
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

  /** Alias matching backend key `road_segment_id` */
  road_segment_id?: string;

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

  /** Road polyline geometry coordinates [[lat, lon], ...] */
  geometry?: [number, number][];
}
