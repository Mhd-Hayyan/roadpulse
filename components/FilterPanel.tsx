"use client";

import React from "react";
import { EventGlyph } from "@/components/EventGlyph";
import type { EventType, RoadEvent } from "@/lib/types";

export interface FilterState {
  activeTypes: Record<EventType, boolean>;
  minSeverity: number;
  minConfidence: number;
  showHeatmapLayer: boolean;
}

interface FilterPanelProps {
  filters: FilterState;
  allEvents: RoadEvent[];
  onFilterChange: (updated: Partial<FilterState>) => void;
  onResetFilters: () => void;
  totalFilteredCount: number;
  totalEventsCount: number;
}

const TYPES: { type: EventType; label: string }[] = [
  { type: "pothole", label: "Pothole" },
  { type: "speed_breaker", label: "Speed Breaker" },
  { type: "rough_patch", label: "Rough Patch" },
];

export default function FilterPanel({
  filters,
  allEvents,
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

  return (
    <div className="w-56 overflow-hidden rounded-xl border border-border bg-background/95 shadow-md backdrop-blur select-none">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-border px-3.5 py-2.5">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold tracking-tight text-foreground">
            Filters
          </h2>
          <span className="rounded-full bg-secondary px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
            {totalFilteredCount}/{totalEventsCount}
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

      <div className="space-y-3.5 px-3 py-3">
        {/* Event Type List */}
        <div className="space-y-1.5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Event type
          </p>
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
                  className={`flex w-full items-center gap-2 rounded-lg border px-2 py-1.5 text-left transition-colors ${
                    active
                      ? "border-border bg-secondary"
                      : "border-transparent bg-transparent opacity-45 hover:opacity-80"
                  }`}
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-md bg-background text-foreground shadow-2xs">
                    <EventGlyph type={type} className="h-4 w-4" />
                  </span>
                  <span className="flex-1 text-sm font-medium text-foreground">
                    {label}
                  </span>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {count}
                  </span>
                  <span
                    className={`flex h-4 w-4 items-center justify-center rounded-[5px] border ${
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
                        aria-hidden
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

        {/* Min Severity Slider */}
        <RangeControl
          label="Min severity"
          value={filters.minSeverity}
          onChange={(v) => onFilterChange({ minSeverity: v })}
        />

        {/* Min Confidence Slider */}
        <RangeControl
          label="Min confidence"
          value={Math.round(filters.minConfidence * 100)}
          onChange={(v) => onFilterChange({ minConfidence: v / 100 })}
        />

        {/* Road condition overlay toggle */}
        <label className="flex cursor-pointer items-center justify-between border-t border-border pt-3">
          <span className="text-sm font-medium text-foreground">
            Road condition overlay
          </span>
          <span className="relative inline-flex">
            <input
              type="checkbox"
              className="peer sr-only"
              checked={filters.showHeatmapLayer}
              onChange={(e) =>
                onFilterChange({ showHeatmapLayer: e.target.checked })
              }
            />
            <span className="h-5 w-9 rounded-full bg-input transition-colors peer-checked:bg-foreground" />
            <span className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-background shadow-xs transition-transform peer-checked:translate-x-4" />
          </span>
        </label>
      </div>
    </div>
  );
}

function RangeControl({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        <span className="text-xs font-semibold tabular-nums text-foreground">
          ≥ {value}%
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-foreground cursor-pointer h-1.5 bg-secondary rounded-lg"
      />
    </div>
  );
}
