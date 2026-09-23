/**
 * lib/data.ts
 *
 * Data Access Layer for RoadPulse.
 *
 * Provides async functions to fetch road anomaly events and segment summaries.
 * Currently backed by mock data (lib/mockData.ts).
 *
 * In production / backend integration:
 * Replace the return statements in fetchRoadEvents() and fetchRoadSegments()
 * with actual fetch() calls to the Python REST API (e.g. GET /api/events).
 * UI components consuming these functions will require ZERO code changes.
 */

import type { RoadEvent, RoadSegment, EventType } from "./types";
import { MOCK_EVENTS, MOCK_SEGMENTS } from "./mockData";

export interface EventFilterOptions {
  eventType?: EventType | "all";
  minSeverity?: number;
  segmentId?: string;
}

/**
 * Fetch road anomaly events, with optional filtering.
 */
export async function getRoadEvents(filters?: EventFilterOptions): Promise<RoadEvent[]> {
  // Simulate asynchronous network delay (100ms)
  await new Promise((resolve) => setTimeout(resolve, 100));

  let events = [...MOCK_EVENTS];

  if (filters?.eventType && filters.eventType !== "all") {
    events = events.filter((e) => e.event_type === filters.eventType);
  }

  if (filters?.minSeverity !== undefined) {
    events = events.filter((e) => e.severity >= filters.minSeverity!);
  }

  if (filters?.segmentId) {
    events = events.filter((e) => e.road_segment_id === filters.segmentId);
  }

  return events;
}

/**
 * Fetch summary information for all road segments.
 */
export async function getRoadSegments(): Promise<RoadSegment[]> {
  // Simulate asynchronous network delay (100ms)
  await new Promise((resolve) => setTimeout(resolve, 100));

  return [...MOCK_SEGMENTS];
}

/**
 * Fetch a single road segment by its ID.
 */
export async function getRoadSegmentById(id: string): Promise<RoadSegment | null> {
  await new Promise((resolve) => setTimeout(resolve, 100));

  const segment = MOCK_SEGMENTS.find((s) => s.id === id);
  return segment || null;
}
