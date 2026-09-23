/**
 * lib/data.ts
 *
 * Data Access Layer for RoadPulse.
 *
 * Connects directly to the live ROADPULSE FastAPI backend (http://localhost:8000).
 * Strictly requires the live backend to be running — does NOT silently fall back to mock data.
 */

import type { RoadEvent, RoadSegment, EventType } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export interface EventFilterOptions {
  eventType?: EventType | "all";
  segmentId?: string;
}

/**
 * Check if the ROADPULSE FastAPI backend is alive and healthy.
 */
export async function checkApiHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
    if (!res.ok) return false;
    const data = await res.json();
    return data.status === "ok";
  } catch {
    return false;
  }
}

/**
 * Fetch real road anomaly events from FastAPI GET /events.
 * Throws an Error if the backend is unreachable.
 */
export async function getRoadEvents(filters?: EventFilterOptions): Promise<RoadEvent[]> {
  const res = await fetch(`${API_BASE_URL}/events`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch events from API (status ${res.status})`);
  }
  let events: RoadEvent[] = await res.json();

  if (filters?.eventType && filters.eventType !== "all") {
    events = events.filter((e) => e.event_type === filters.eventType);
  }

  if (filters?.segmentId && filters.segmentId !== "all") {
    events = events.filter((e) => e.road_segment_id === filters.segmentId);
  }

  return events;
}

/**
 * Fetch real scored road segments from FastAPI GET /segments.
 * Throws an Error if the backend is unreachable.
 */
export async function getRoadSegments(): Promise<RoadSegment[]> {
  const res = await fetch(`${API_BASE_URL}/segments`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch segments from API (status ${res.status})`);
  }
  return await res.json();
}

/**
 * Fetch a single road segment by its ID from the live API.
 */
export async function getRoadSegmentById(id: string): Promise<RoadSegment | null> {
  const segments = await getRoadSegments();
  return segments.find((s) => s.id === id || s.road_segment_id === id) || null;
}
