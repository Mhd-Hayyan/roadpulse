"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import dynamic from "next/dynamic";
import Header from "@/components/Header";
import FilterPanel, { type FilterState } from "@/components/FilterPanel";
import DetailsPanel from "@/components/DetailsPanel";
import Legend from "@/components/Legend";
import SegmentTable from "@/components/SegmentTable";
import { getRoadEvents, getRoadSegments } from "@/lib/data";
import type { RoadEvent, RoadSegment } from "@/lib/types";

// Dynamically import Leaflet map component with ssr: false
const MapView = dynamic(() => import("@/components/Map/MapView"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-muted">
      <div className="flex items-center gap-2.5 text-sm text-muted-foreground">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground" />
        <span>Loading sensing corridor map...</span>
      </div>
    </div>
  ),
});

const DEFAULT_FILTERS: FilterState = {
  activeTypes: {
    pothole: true,
    speed_breaker: true,
    rough_patch: true,
  },
  selectedSegmentId: "all",
  selectedSeverityLabel: "all",
};

export default function Home() {
  const [allEvents, setAllEvents] = useState<RoadEvent[]>([]);
  const [allSegments, setAllSegments] = useState<RoadSegment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [selectedEvent, setSelectedEvent] = useState<RoadEvent | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<RoadSegment | null>(null);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  // Initialize theme from localStorage or default to dark-first aesthetic
  useEffect(() => {
    const savedTheme = localStorage.getItem("roadpulse-theme") as "dark" | "light" | null;
    const initialTheme = savedTheme || "dark";
    setTheme(initialTheme);
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(initialTheme);
  }, []);

  const handleToggleTheme = () => {
    setTheme((prev) => {
      const next: "dark" | "light" = prev === "dark" ? "light" : "dark";
      const root = document.documentElement;
      root.classList.remove("light", "dark");
      root.classList.add(next);
      localStorage.setItem("roadpulse-theme", next);
      return next;
    });
  };

  // Load real API data from FastAPI backend strictly (NO mock fallback)
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [eventsData, segmentsData] = await Promise.all([
        getRoadEvents(),
        getRoadSegments(),
      ]);
      setAllEvents(eventsData);
      setAllSegments(segmentsData);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to connect to backend";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filter events based strictly on authentic API properties
  const filteredEvents = useMemo(() => {
    return allEvents.filter((event) => {
      // 1. Filter by anomaly type
      if (!filters.activeTypes[event.event_type]) {
        return false;
      }
      // 2. Filter by road segment ID
      if (filters.selectedSegmentId !== "all") {
        const segId = event.road_segment_id || (event as { segmentId?: string }).segmentId;
        if (segId !== filters.selectedSegmentId) {
          return false;
        }
      }
      // 3. Filter by parent segment M11 severity label
      if (filters.selectedSeverityLabel !== "all") {
        const parentSegment = allSegments.find(
          (s) => (s.road_segment_id || s.id) === event.road_segment_id
        );
        if (parentSegment?.severity_label !== filters.selectedSeverityLabel) {
          return false;
        }
      }
      return true;
    });
  }, [allEvents, allSegments, filters]);

  // Authentic KPI metrics calculated exclusively from real API data
  const metrics = useMemo(() => {
    const totalSegments = allSegments.length;
    const totalEvents = allEvents.length;
    const potholesCount = allEvents.filter((e) => e.event_type === "pothole").length;
    const speedBreakersCount = allEvents.filter((e) => e.event_type === "speed_breaker").length;
    const roughPatchesCount = allEvents.filter((e) => e.event_type === "rough_patch").length;

    const maxPasses = allSegments.reduce((max, s) => {
      const p = s.unique_pass_count ?? s.busPasses ?? 0;
      return p > max ? p : max;
    }, 0);

    const highOrCriticalSegments = allSegments.filter(
      (s) => s.severity_label === "critical" || s.severity_label === "high"
    ).length;

    return {
      totalSegments,
      totalEvents,
      potholesCount,
      speedBreakersCount,
      roughPatchesCount,
      maxPasses,
      highOrCriticalSegments,
    };
  }, [allSegments, allEvents]);

  const handleFilterChange = (updated: Partial<FilterState>) => {
    setFilters((prev) => ({ ...prev, ...updated }));
  };

  const handleResetFilters = () => {
    setFilters(DEFAULT_FILTERS);
  };

  const handleSelectEvent = (event: RoadEvent) => {
    setSelectedSegment(null);
    setSelectedEvent(event);
  };

  const handleSelectSegment = (segment: RoadSegment) => {
    setSelectedEvent(null);
    setSelectedSegment(segment);
  };

  const handleCloseDetails = () => {
    setSelectedEvent(null);
    setSelectedSegment(null);
  };

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground transition-colors font-sans antialiased">
      {/* 1. Header with branding, corridor context, Live API badge, and theme switch */}
      <Header
        theme={theme}
        onToggleTheme={handleToggleTheme}
        isConnected={!error}
        onRefresh={loadData}
        isLoading={loading}
      />

      {/* 2. Main Workspace */}
      {error ? (
        /* BACKEND DISCONNECTED screen (Strict: ZERO fallback to mock data) */
        <main className="flex-1 flex items-center justify-center p-6">
          <div className="max-w-md w-full rounded-2xl border border-red-500/30 bg-card p-6 text-center shadow-lg">
            <div className="w-12 h-12 mx-auto rounded-full bg-red-500/10 text-red-500 flex items-center justify-center mb-4">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h2 className="text-lg font-bold tracking-tight text-foreground mb-1.5">
              BACKEND DISCONNECTED
            </h2>
            <p className="text-xs text-muted-foreground mb-4">
              Unable to reach the live ROADPULSE FastAPI server at{" "}
              <code className="bg-secondary px-1.5 py-0.5 rounded font-mono text-foreground">
                http://localhost:8000
              </code>
              . Mock fallback is disabled to guarantee validation against authentic sensing data.
            </p>
            <div className="bg-secondary rounded-lg p-2.5 mb-5 text-left font-mono text-[11px] text-muted-foreground border border-border">
              <span className="text-muted-foreground/60 block mb-0.5"># Start backend with:</span>
              <span className="text-foreground">uvicorn src.api.main:app --port 8000</span>
            </div>
            <button
              onClick={loadData}
              disabled={loading}
              className="w-full py-2 rounded-lg bg-foreground text-background font-semibold text-xs transition-opacity hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-1.5"
            >
              <svg
                className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              <span>Retry Connection</span>
            </button>
          </div>
        </main>
      ) : (
        <main className="flex-1 flex flex-col p-4 sm:p-5 gap-4 overflow-x-hidden">
          {/* Authentic KPI Summary Cards */}
          <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
              <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Monitored Segments
              </div>
              <div className="text-2xl font-bold tracking-tight text-foreground mt-0.5">
                {metrics.totalSegments}
              </div>
              <div className="text-[10px] text-muted-foreground mt-0.5">NH66 Corridor</div>
            </div>

            <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
              <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Total Detections
              </div>
              <div className="text-2xl font-bold tracking-tight text-blue-500 mt-0.5">
                {metrics.totalEvents}
              </div>
              <div className="text-[10px] text-muted-foreground mt-0.5">
                Across {metrics.maxPasses} Bus Passes
              </div>
            </div>

            <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
              <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Potholes
              </div>
              <div className="text-2xl font-bold tracking-tight text-red-500 mt-0.5">
                {metrics.potholesCount}
              </div>
              <div className="text-[10px] text-muted-foreground mt-0.5">Vertical impact shocks</div>
            </div>

            <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
              <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Speed Breakers
              </div>
              <div className="text-2xl font-bold tracking-tight text-amber-500 mt-0.5">
                {metrics.speedBreakersCount}
              </div>
              <div className="text-[10px] text-muted-foreground mt-0.5">Pitch &amp; heave swings</div>
            </div>

            <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
              <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Rough Patches
              </div>
              <div className="text-2xl font-bold tracking-tight text-sky-500 mt-0.5">
                {metrics.roughPatchesCount}
              </div>
              <div className="text-[10px] text-muted-foreground mt-0.5">Sustained vibrations</div>
            </div>

            <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
              <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                High / Critical (M11)
              </div>
              <div className="text-2xl font-bold tracking-tight text-rose-500 mt-0.5">
                {metrics.highOrCriticalSegments}
              </div>
              <div className="text-[10px] text-muted-foreground mt-0.5">
                Prototype severity rating
              </div>
            </div>
          </section>

          {/* Map Viewport with Floating Overlays */}
          <section className="relative w-full h-[520px] rounded-2xl overflow-hidden border border-border bg-card shadow-sm">
            {/* Real Sensed Coordinate Map */}
            <MapView
              events={filteredEvents}
              segments={allSegments}
              selectedEventId={selectedEvent?.event_id ?? null}
              selectedSegmentId={
                selectedSegment ? selectedSegment.road_segment_id || selectedSegment.id : null
              }
              onSelectEvent={handleSelectEvent}
              onSelectSegment={handleSelectSegment}
            />

            {/* Left floating overlay: FilterPanel + Compact Legend at bottom */}
            <div className="pointer-events-none absolute inset-y-0 left-0 z-[500] flex flex-col justify-between p-3.5">
              <div className="pointer-events-auto">
                <FilterPanel
                  filters={filters}
                  allEvents={allEvents}
                  allSegments={allSegments}
                  onFilterChange={handleFilterChange}
                  onResetFilters={handleResetFilters}
                  totalFilteredCount={filteredEvents.length}
                  totalEventsCount={allEvents.length}
                />
              </div>
              <div className="pointer-events-auto mt-2">
                <Legend />
              </div>
            </div>

            {/* Right floating overlay: Contextual Details Card */}
            <div className="pointer-events-none absolute inset-y-0 right-0 z-[500] flex flex-col justify-start p-3.5">
              <div className="pointer-events-auto">
                <DetailsPanel
                  selectedEvent={selectedEvent}
                  selectedSegment={selectedSegment}
                  allSegments={allSegments}
                  onClose={handleCloseDetails}
                  onViewSegment={handleSelectSegment}
                  onFilterBySegment={(segId) => handleFilterChange({ selectedSegmentId: segId })}
                />
              </div>
            </div>
          </section>

          {/* Scored Road Segments Table (M11 Multi-Pass Scoring Invariant) */}
          <section>
            <SegmentTable
              segments={allSegments}
              selectedSegmentId={
                selectedSegment ? selectedSegment.road_segment_id || selectedSegment.id : null
              }
              onSelectSegment={handleSelectSegment}
            />
          </section>
        </main>
      )}

      {/* Footer */}
      <footer className="border-t border-border bg-background px-5 py-3 text-center text-xs text-muted-foreground select-none">
        ROADPULSE &copy; 2026 — Bus Fleet as a Mobile Road-Condition Sensing Network
      </footer>
    </div>
  );
}
