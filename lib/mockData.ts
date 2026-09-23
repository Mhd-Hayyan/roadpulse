/**
 * lib/mockData.ts
 *
 * Realistic mock dataset for RoadPulse frontend development and testing.
 * Coordinates cover the Kochi / Ernakulam bus corridor in Kerala, India.
 *
 * Includes:
 * - 3 Event Types: pothole, speed_breaker, rough_patch
 * - Varied severities (0 - 100) and confidence scores (0.0 - 1.0)
 * - Multiple events grouped by road segments (e.g., segment_014, segment_015)
 * - Varied bus pass counts
 */

import type { RoadEvent, RoadSegment } from "./types";

export const MOCK_EVENTS: RoadEvent[] = [
  // --- Segment 014: MG Road (Ernakulam North to South) ---
  {
    event_id: "evt_001",
    event_type: "pothole",
    latitude: 9.9725,
    longitude: 76.2783,
    road_segment_id: "segment_014",
    severity: 85,
    confidence: 0.94,
    pass_count: 12,
    id: "evt_001",
    eventType: "pothole",
    segmentId: "segment_014",
    busPasses: 12,
  },
  {
    event_id: "evt_002",
    event_type: "rough_patch",
    latitude: 9.9681,
    longitude: 76.2798,
    road_segment_id: "segment_014",
    severity: 62,
    confidence: 0.88,
    pass_count: 9,
    id: "evt_002",
    eventType: "rough_patch",
    segmentId: "segment_014",
    busPasses: 9,
  },
  {
    event_id: "evt_003",
    event_type: "speed_breaker",
    latitude: 9.9614,
    longitude: 76.2815,
    road_segment_id: "segment_014",
    severity: 35,
    confidence: 0.99,
    pass_count: 18,
    id: "evt_003",
    eventType: "speed_breaker",
    segmentId: "segment_014",
    busPasses: 18,
  },

  // --- Segment 015: Kaloor - Edappally Stretch (NH 66 Corridor) ---
  {
    event_id: "evt_004",
    event_type: "pothole",
    latitude: 9.9982,
    longitude: 76.3012,
    road_segment_id: "segment_015",
    severity: 92,
    confidence: 0.96,
    pass_count: 15,
    id: "evt_004",
    eventType: "pothole",
    segmentId: "segment_015",
    busPasses: 15,
  },
  {
    event_id: "evt_005",
    event_type: "pothole",
    latitude: 10.0035,
    longitude: 76.3055,
    road_segment_id: "segment_015",
    severity: 78,
    confidence: 0.89,
    pass_count: 11,
    id: "evt_005",
    eventType: "pothole",
    segmentId: "segment_015",
    busPasses: 11,
  },
  {
    event_id: "evt_006",
    event_type: "rough_patch",
    latitude: 10.0112,
    longitude: 76.3118,
    road_segment_id: "segment_015",
    severity: 54,
    confidence: 0.75,
    pass_count: 6,
    id: "evt_006",
    eventType: "rough_patch",
    segmentId: "segment_015",
    busPasses: 6,
  },

  // --- Segment 016: Vytilla Mobility Hub - Palarivattom ---
  {
    event_id: "evt_007",
    event_type: "speed_breaker",
    latitude: 9.9668,
    longitude: 76.3182,
    road_segment_id: "segment_016",
    severity: 40,
    confidence: 0.97,
    pass_count: 24,
    id: "evt_007",
    eventType: "speed_breaker",
    segmentId: "segment_016",
    busPasses: 24,
  },
  {
    event_id: "evt_008",
    event_type: "rough_patch",
    latitude: 9.9795,
    longitude: 76.3121,
    road_segment_id: "segment_016",
    severity: 70,
    confidence: 0.83,
    pass_count: 8,
    id: "evt_008",
    eventType: "rough_patch",
    segmentId: "segment_016",
    busPasses: 8,
  },

  // --- Segment 017: Kakkanad Infopark Road ---
  {
    event_id: "evt_009",
    event_type: "pothole",
    latitude: 10.0128,
    longitude: 76.3614,
    road_segment_id: "segment_017",
    severity: 45,
    confidence: 0.81,
    pass_count: 5,
    id: "evt_009",
    eventType: "pothole",
    segmentId: "segment_017",
    busPasses: 5,
  },
  {
    event_id: "evt_010",
    event_type: "speed_breaker",
    latitude: 10.0091,
    longitude: 76.3530,
    road_segment_id: "segment_017",
    severity: 30,
    confidence: 0.92,
    pass_count: 14,
    id: "evt_010",
    eventType: "speed_breaker",
    segmentId: "segment_017",
    busPasses: 14,
  }
];

export const MOCK_SEGMENTS: RoadSegment[] = [
  {
    id: "segment_014",
    name: "MG Road (Ernakulam North - South)",
    conditionScore: 58,
    eventCount: 3,
    potholeCount: 1,
    speedBreakerCount: 1,
    roughPatchCount: 1,
    busPasses: 18,
    confidence: 0.93,
  },
  {
    id: "segment_015",
    name: "Kaloor - Edappally Stretch (NH 66)",
    conditionScore: 42,
    eventCount: 3,
    potholeCount: 2,
    speedBreakerCount: 0,
    roughPatchCount: 1,
    busPasses: 15,
    confidence: 0.87,
  },
  {
    id: "segment_016",
    name: "Vytilla Mobility Hub - Palarivattom",
    conditionScore: 68,
    eventCount: 2,
    potholeCount: 0,
    speedBreakerCount: 1,
    roughPatchCount: 1,
    busPasses: 24,
    confidence: 0.90,
  },
  {
    id: "segment_017",
    name: "Kakkanad Infopark Road",
    conditionScore: 79,
    eventCount: 2,
    potholeCount: 1,
    speedBreakerCount: 1,
    roughPatchCount: 0,
    busPasses: 14,
    confidence: 0.86,
  },
];
