"use client";

import React from "react";
import { EventGlyph } from "@/components/EventGlyph";
import type { EventType, RoadEvent, RoadSegment } from "@/lib/types";

export interface FilterState {
  activeTypes: Record<EventType, boolean>;
  selectedSegmentId: string | "all";
  selectedSeverityLabel: string | "all";
}

interface FilterPanelProps {
  filters: FilterState;
  allEvents: RoadEvent[];
  allSegments: RoadSegment[];
  onFilterChange: (updated: Partial<FilterState>) => void;
  onResetFilters: () => void;
  totalFilteredCount: number;
  totalEventsCount: number;
}

const TYPES: { type: EventType; label: string }[] = [
  { type: "pothole", label: "Potholes" },
  { type: "speed_breaker", label: "Speed Breakers" },
  { type: "rough_patch", label: "Rough Patches" },
];

export default function FilterPanel({
  filters,
  allEvents,
  allSegments,
  onFilterChange,
  onResetFilters,
  totalFilteredCount,
  totalEventsCount,
}: FilterPanelProps) {
  const toggleType = (t: EventType) => {
    onFilterChange({
      activeTypes: {
        ...filters.activeTypes,
        [t]: !filters.activeTypes[t],
      },
    });
  };

  const selectAllTypes = () => {
    onFilterChange({
      activeTypes: {
        pothole: true,
        speed_breaker: true,
        rough_patch: true,
      },
    });
  };

  return (
    <div className="w-64 overflow-hidden rounded-xl border border-border bg-background/95 shadow-lg backdrop-blur select-none text-xs">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-border px-3.5 py-2.5">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold tracking-tight text-foreground">
            Filters
          </h2>
          <span className="rounded-full bg-secondary px-2 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
            {totalFilteredCount} / {totalEventsCount}
          </span>
        </div>
        <button
          type="button"
          onClick={onResetFilters}
          className="text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          Reset
        </button>
      </div>

      <div className="space-y-4 px-3.5 py-3">
        {/* Event Type Checkboxes */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Anomaly Type
            </p>
            <button
              type="button"
              onClick={selectAllTypes}
              className="text-[10px] text-muted-foreground hover:text-foreground"
            >
              Select All
            </button>
          </div>

          <div className="space-y-1">
            {TYPES.map(({ type, label }) => {
              const active = filters.activeTypes[type];
              const count = allEvents.filter((e) => e.event_type === type).length;

              return (
                <button
                  key={type}
                  type="button"
                  onClick={() => toggleType(type)}
                  aria-pressed={active}
                  className={`flex w-full items-center gap-2 rounded-lg border px-2.5 py-1.5 text-left transition-colors ${
                    active
                      ? "border-border bg-secondary"
                      : "border-transparent bg-transparent opacity-45 hover:opacity-80"
                  }`}
                >
                  <span
                    className={`flex h-6 w-6 items-center justify-center rounded-md text-white shadow-2xs ${
                      type === "pothole"
                        ? "bg-red-600"
                        : type === "speed_breaker"
                        ? "bg-amber-600"
                        : "bg-blue-600"
                    }`}
                  >
                    <EventGlyph type={type} className="h-3.5 w-3.5" />
                  </span>
                  <span className="flex-1 text-xs font-medium text-foreground">
                    {label}
                  </span>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {count}
                  </span>
                  <span
                    className={`flex h-4 w-4 items-center justify-center rounded-[4px] border ${
                      active
                        ? "border-foreground bg-foreground text-background"
                        : "border-border"
                    }`}
                  >
                    {active && (
                      <svg
                        viewBox="0 0 24 24"
                        className="h-3 w-3"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        aria-hidden="true"
                      >
                        <path d="M5 13l4 4L19 7" strokeLinecap="round" />
                      </svg>
                    )}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Road Segment Filter */}
        <div className="space-y-1.5 pt-2 border-t border-border">
          <label
            htmlFor="filter-segment"
            className="block text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
          >
            Road Segment
          </label>
          <select
            id="filter-segment"
            value={filters.selectedSegmentId}
            onChange={(e) => onFilterChange({ selectedSegmentId: e.target.value })}
            className="w-full rounded-lg border border-border bg-secondary px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="all">All Segments ({allSegments.length})</option>
            {allSegments.map((s) => {
              const segId = s.road_segment_id || s.id;
              const cond = s.primary_condition?.replace("_", " ") || "mixed";
              return (
                <option key={segId} value={segId}>
                  {segId} ({cond})
                </option>
              );
            })}
          </select>
        </div>

        {/* Segment Severity Filter (Authoritative M11 Scoring) */}
        <div className="space-y-1.5 pt-2 border-t border-border">
          <label
            htmlFor="filter-severity"
            className="block text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
          >
            Segment Severity (M11)
          </label>
          <select
            id="filter-severity"
            value={filters.selectedSeverityLabel}
            onChange={(e) => onFilterChange({ selectedSeverityLabel: e.target.value })}
            className="w-full rounded-lg border border-border bg-secondary px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="all">All Severity Levels</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="moderate">Moderate</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>
    </div>
  );
}
