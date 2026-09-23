"use client";

import React, { useEffect, useState, useMemo } from "react";
import dynamic from "next/dynamic";
import Header from "@/components/Header";
import FilterPanel, { type FilterState } from "@/components/FilterPanel";
import DetailsPanel from "@/components/DetailsPanel";
import Legend from "@/components/Legend";
import { getRoadEvents, getRoadSegments } from "@/lib/data";
import type { RoadEvent, RoadSegment } from "@/lib/types";

// Dynamically import Leaflet map component with ssr: false to prevent window/document errors during Next.js SSR build
const MapView = dynamic(() => import("@/components/Map/MapView"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-muted">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-muted-foreground/40 border-t-foreground" />
        Loading corridor map…
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
  minSeverity: 0,
  minConfidence: 0.0,
  showHeatmapLayer: true,
};

export default function Home() {
  const [allEvents, setAllEvents] = useState<RoadEvent[]>([]);
  const [allSegments, setAllSegments] = useState<RoadSegment[]>([]);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  const [selectedEvent, setSelectedEvent] = useState<RoadEvent | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<RoadSegment | null>(
    null
  );

  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  // Initialize theme from localStorage or default to dark
  useEffect(() => {
    const savedTheme = localStorage.getItem("roadpulse-theme") as
      | "dark"
      | "light"
      | null;
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

  // Load initial data from lib/data.ts
  useEffect(() => {
    async function loadData() {
      try {
        const [eventsData, segmentsData] = await Promise.all([
          getRoadEvents(),
          getRoadSegments(),
        ]);
        setAllEvents(eventsData);
        setAllSegments(segmentsData);
      } catch (err) {
        console.error("Failed to load road data:", err);
      }
    }
    loadData();
  }, []);

  // Filter events based on active UI filter state (independent ON/OFF controls, severity, confidence)
  const filteredEvents = useMemo(() => {
    return allEvents.filter((event) => {
      if (!filters.activeTypes[event.event_type]) {
        return false;
      }
      if (event.severity < filters.minSeverity) {
        return false;
      }
      if (event.confidence < filters.minConfidence) {
        return false;
      }
      return true;
    });
  }, [allEvents, filters]);

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
    <div className="flex h-screen flex-col bg-background text-foreground transition-colors overflow-hidden select-none">
      {/* 1. Header */}
      <Header theme={theme} onToggleTheme={handleToggleTheme} />

      {/* 2. Main Map Viewport with Floating Overlays */}
      <main className="relative flex-1 overflow-hidden">
        {/* Leaflet Map Hero */}
        <MapView
          events={filteredEvents}
          segments={allSegments}
          selectedEventId={selectedEvent?.event_id ?? null}
          selectedSegmentId={selectedSegment?.id ?? null}
          showHeatmapLayer={filters.showHeatmapLayer}
          onSelectEvent={handleSelectEvent}
          onSelectSegment={handleSelectSegment}
        />

        {/* Left floating overlay: FilterPanel + Compact Legend at bottom */}
        <div className="pointer-events-none absolute inset-y-0 left-0 z-[500] flex flex-col justify-between p-4">
          <div className="pointer-events-auto">
            <FilterPanel
              filters={filters}
              allEvents={allEvents}
              onFilterChange={handleFilterChange}
              onResetFilters={handleResetFilters}
              totalFilteredCount={filteredEvents.length}
              totalEventsCount={allEvents.length}
            />
          </div>
          <div className="pointer-events-auto">
            <Legend />
          </div>
        </div>

        {/* Right floating overlay: Contextual Details Card */}
        <div className="pointer-events-none absolute inset-y-0 right-0 z-[500] flex flex-col justify-start p-4">
          <div className="pointer-events-auto">
            <DetailsPanel
              selectedEvent={selectedEvent}
              selectedSegment={selectedSegment}
              allSegments={allSegments}
              onClose={handleCloseDetails}
              onViewSegment={handleSelectSegment}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
