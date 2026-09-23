"use client";

import React from "react";
import { EventGlyph } from "@/components/EventGlyph";
import type { RoadEvent, RoadSegment, EventType } from "@/lib/types";

interface DetailsPanelProps {
  selectedEvent: RoadEvent | null;
  selectedSegment: RoadSegment | null;
  allSegments: RoadSegment[];
  onClose: () => void;
  onViewSegment: (segment: RoadSegment) => void;
  onFilterBySegment?: (segmentId: string) => void;
}

const EVENT_LABELS: Record<EventType, string> = {
  pothole: "Pothole",
  speed_breaker: "Speed Breaker",
  rough_patch: "Rough Patch",
};

function getSeverityColor(label?: string): string {
  if (label === "critical") return "#dc2626";
  if (label === "high") return "#ea580c";
  if (label === "moderate") return "#d97706";
  return "#16a34a";
}

function getConfidenceColor(label?: string): string {
  if (label?.includes("high")) return "#059669";
  if (label?.includes("moderate")) return "#0284c7";
  return "#64748b";
}

export default function DetailsPanel({
  selectedEvent,
  selectedSegment,
  allSegments,
  onClose,
  onViewSegment,
  onFilterBySegment,
}: DetailsPanelProps) {
  if (!selectedEvent && !selectedSegment) {
    return null;
  }

  return (
    <div className="w-80 overflow-hidden rounded-xl border border-border bg-background/95 shadow-xl backdrop-blur select-none text-xs">
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5 bg-secondary/50">
        <span className="font-semibold uppercase tracking-wider text-[10px] text-muted-foreground">
          {selectedEvent ? "Event Inspection" : "Segment Intelligence (M11)"}
        </span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close details"
          className="flex h-5 w-5 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        >
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* ============================================================== */}
        {/* EVENT DETAIL (Strictly real API fields, NO fake severity/confidence) */}
        {/* ============================================================== */}
        {selectedEvent && (
          <div className="space-y-3.5">
            {/* Title with Event Type Badge */}
            <div className="flex items-start gap-3">
              <span
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-white shadow-2xs ${
                  selectedEvent.event_type === "pothole"
                    ? "bg-red-600"
                    : selectedEvent.event_type === "speed_breaker"
                    ? "bg-amber-600"
                    : "bg-blue-600"
                }`}
              >
                <EventGlyph type={selectedEvent.event_type} className="h-4.5 w-4.5" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-sm text-foreground truncate">
                    {EVENT_LABELS[selectedEvent.event_type]}
                  </h3>
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {selectedEvent.event_id}
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Pre-scoring signal detection on bus pass #{selectedEvent.pass_id ?? 1}
                </p>
              </div>
            </div>

            {/* Note clarifying event-level vs segment-level data */}
            <div className="rounded-lg bg-secondary/80 border border-border px-2.5 py-1.5 text-[11px] text-muted-foreground">
              <em>Note:</em> Severity and confidence are aggregated at the road-segment level across all bus passes.
            </div>

            {/* Event Metrics Table */}
            <dl className="grid grid-cols-2 gap-x-3 gap-y-2 border-t border-border pt-3">
              <div>
                <dt className="text-[11px] text-muted-foreground">Road Segment</dt>
                <dd className="font-mono font-bold text-foreground">
                  {selectedEvent.road_segment_id}
                </dd>
              </div>

              <div>
                <dt className="text-[11px] text-muted-foreground">Bus Pass</dt>
                <dd className="font-medium text-foreground">
                  Pass #{selectedEvent.pass_id ?? 1}
                </dd>
              </div>

              {typeof selectedEvent.duration === "number" && (
                <div>
                  <dt className="text-[11px] text-muted-foreground">Duration</dt>
                  <dd className="font-medium text-foreground">
                    {selectedEvent.duration.toFixed(2)}s
                  </dd>
                </div>
              )}

              {typeof selectedEvent.start_time === "number" && (
                <div>
                  <dt className="text-[11px] text-muted-foreground">Timeline</dt>
                  <dd className="font-medium text-foreground">
                    {selectedEvent.start_time.toFixed(1)}s – {selectedEvent.end_time?.toFixed(1)}s
                  </dd>
                </div>
              )}

              {selectedEvent.map_match_status && (
                <div>
                  <dt className="text-[11px] text-muted-foreground">Map Match</dt>
                  <dd className="font-medium text-emerald-600 dark:text-emerald-400 capitalize">
                    {selectedEvent.map_match_status}
                  </dd>
                </div>
              )}

              {selectedEvent.gps_quality && (
                <div>
                  <dt className="text-[11px] text-muted-foreground">GPS Quality</dt>
                  <dd className="font-medium text-foreground capitalize">
                    {selectedEvent.gps_quality}
                  </dd>
                </div>
              )}

              <div className="col-span-2 pt-1 border-t border-border/50">
                <dt className="text-[11px] text-muted-foreground">Coordinates</dt>
                <dd className="font-mono text-[11px] text-foreground">
                  {selectedEvent.latitude.toFixed(5)}, {selectedEvent.longitude.toFixed(5)}
                </dd>
              </div>
            </dl>

            {/* Action to switch to parent segment */}
            {(() => {
              const parent = allSegments.find(
                (s) => (s.road_segment_id || s.id) === selectedEvent.road_segment_id
              );
              if (!parent) return null;
              return (
                <button
                  type="button"
                  onClick={() => onViewSegment(parent)}
                  className="w-full flex items-center justify-between rounded-lg border border-border px-3 py-2 text-xs font-semibold text-foreground bg-secondary/60 hover:bg-secondary transition-colors"
                >
                  <span>Inspect Segment {selectedEvent.road_segment_id}</span>
                  <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              );
            })()}
          </div>
        )}

        {/* ============================================================== */}
        {/* SEGMENT DETAIL (Authoritative M11 Multi-Pass Scoring) */}
        {/* ============================================================== */}
        {!selectedEvent && selectedSegment && (
          <div className="space-y-3.5">
            {/* Segment Title & Primary Condition */}
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">
                  Road Segment
                </p>
                <h3 className="font-mono font-bold text-base text-foreground">
                  {selectedSegment.road_segment_id || selectedSegment.id}
                </h3>
              </div>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold capitalize bg-secondary border border-border text-foreground">
                {(selectedSegment.primary_condition || "none").replace("_", " ")}
              </span>
            </div>

            {/* M11 Severity & Confidence Scoring Meters */}
            <div className="space-y-2.5 rounded-lg border border-border bg-secondary/40 p-3">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] font-semibold text-muted-foreground">
                    Severity Score (M11)
                  </span>
                  <span
                    className="font-bold text-xs uppercase"
                    style={{ color: getSeverityColor(selectedSegment.severity_label) }}
                  >
                    {selectedSegment.severity_label ?? "N/A"} ({selectedSegment.severity_score?.toFixed(1) ?? 0}%)
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, Math.max(0, selectedSegment.severity_score ?? 0))}%`,
                      backgroundColor: getSeverityColor(selectedSegment.severity_label),
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] font-semibold text-muted-foreground">
                    Confidence (Coverage)
                  </span>
                  <span
                    className="font-bold text-xs capitalize"
                    style={{ color: getConfidenceColor(selectedSegment.confidence_label) }}
                  >
                    {selectedSegment.confidence_label?.replace("_", " ") ?? "N/A"} ({selectedSegment.confidence_percent?.toFixed(0) ?? 0}%)
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, Math.max(0, selectedSegment.confidence_percent ?? 0))}%`,
                      backgroundColor: getConfidenceColor(selectedSegment.confidence_label),
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Event Counts & Multi-Pass Coverage */}
            <dl className="space-y-1.5 border-t border-border pt-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Total Events</dt>
                <dd className="font-bold text-foreground">
                  {selectedSegment.total_event_count ?? selectedSegment.eventCount ?? 0}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Bus Passes</dt>
                <dd className="font-medium text-foreground">
                  {selectedSegment.unique_pass_count ?? selectedSegment.busPasses ?? 0} observed ({selectedSegment.pass_ids ?? "all"})
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Potholes</dt>
                <dd className="font-semibold text-red-600 dark:text-red-400">
                  {selectedSegment.pothole_count ?? selectedSegment.potholeCount ?? 0}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Speed Breakers</dt>
                <dd className="font-semibold text-amber-600 dark:text-amber-400">
                  {selectedSegment.speed_breaker_count ?? selectedSegment.speedBreakerCount ?? 0}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Rough Patches</dt>
                <dd className="font-semibold text-blue-600 dark:text-blue-400">
                  {selectedSegment.rough_road_count ?? selectedSegment.roughPatchCount ?? 0}
                </dd>
              </div>
            </dl>

            {onFilterBySegment && (
              <button
                type="button"
                onClick={() =>
                  onFilterBySegment(
                    selectedSegment.road_segment_id || selectedSegment.id
                  )
                }
                className="w-full rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground bg-secondary hover:bg-secondary/80 transition-colors"
              >
                Filter Map to This Segment
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
