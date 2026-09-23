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
}

const EVENT_LABELS: Record<EventType, string> = {
  pothole: "Pothole",
  speed_breaker: "Speed Breaker",
  rough_patch: "Rough Patch",
};

function getConditionMeta(severity: number) {
  if (severity >= 66) {
    return { label: "Severe", color: "#dc2626" };
  }
  if (severity >= 33) {
    return { label: "Warning", color: "#d97706" };
  }
  return { label: "Healthy", color: "#16a34a" };
}

function getSegmentConditionMeta(score: number) {
  if (score >= 75) {
    return { label: "Healthy", color: "#16a34a" };
  }
  if (score >= 50) {
    return { label: "Warning", color: "#d97706" };
  }
  return { label: "Severe", color: "#dc2626" };
}

export default function DetailsPanel({
  selectedEvent,
  selectedSegment,
  allSegments,
  onClose,
  onViewSegment,
}: DetailsPanelProps) {
  if (!selectedEvent && !selectedSegment) return null;

  return (
    <div className="w-80 rounded-xl border border-border bg-background/95 p-4 shadow-lg backdrop-blur select-none">
      <button
        type="button"
        onClick={onClose}
        aria-label="Close details"
        className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
      >
        <svg
          viewBox="0 0 24 24"
          className="h-4 w-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden
        >
          <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
        </svg>
      </button>

      {/* EVENT DETAIL */}
      {selectedEvent && (
        <div className="relative pr-4">
          {(() => {
            const meta = getConditionMeta(selectedEvent.severity);
            const parentSegment = allSegments.find(
              (s) => s.id === selectedEvent.road_segment_id
            );

            return (
              <>
                <div className="flex items-start gap-3">
                  <span
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-white shadow-2xs"
                    style={{ background: meta.color }}
                  >
                    <EventGlyph type={selectedEvent.event_type} className="h-5 w-5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-semibold tracking-tight text-foreground truncate">
                        {EVENT_LABELS[selectedEvent.event_type]}
                      </h3>
                      <span
                        className="inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-semibold"
                        style={{ background: `${meta.color}1a`, color: meta.color }}
                      >
                        {meta.label}
                      </span>
                    </div>
                    <p className="truncate text-xs text-muted-foreground">
                      {selectedEvent.event_id} · {parentSegment?.name || selectedEvent.road_segment_id}
                    </p>
                  </div>
                </div>

                <div className="mt-4 space-y-3">
                  <Meter
                    label="Severity"
                    value={selectedEvent.severity}
                    color={meta.color}
                  />
                  <Meter
                    label="Confidence"
                    value={Math.round(selectedEvent.confidence * 100)}
                  />
                </div>

                <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-border pt-4">
                  <div>
                    <dt className="text-xs text-muted-foreground">Road segment</dt>
                    <dd className="text-sm font-medium text-foreground">
                      {selectedEvent.road_segment_id}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Bus passes</dt>
                    <dd className="text-sm font-medium text-foreground">
                      {selectedEvent.pass_count} observed
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-xs text-muted-foreground">Coordinates</dt>
                    <dd className="text-sm font-medium text-foreground font-mono">
                      {selectedEvent.latitude.toFixed(4)}, {selectedEvent.longitude.toFixed(4)}
                    </dd>
                  </div>
                </dl>

                {parentSegment && (
                  <button
                    type="button"
                    onClick={() => onViewSegment(parentSegment)}
                    className="mt-4 flex w-full items-center justify-between rounded-lg border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary"
                  >
                    <span className="truncate">View {parentSegment.name}</span>
                    <svg
                      viewBox="0 0 24 24"
                      className="h-4 w-4 shrink-0 text-muted-foreground"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      aria-hidden
                    >
                      <path
                        d="M9 6l6 6-6 6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>
                )}
              </>
            );
          })()}
        </div>
      )}

      {/* SEGMENT DETAIL */}
      {!selectedEvent && selectedSegment && (
        <div className="relative pr-4">
          {(() => {
            const meta = getSegmentConditionMeta(selectedSegment.conditionScore);
            const rows = [
              { label: "Events", value: selectedSegment.eventCount, strong: true },
              { label: "Potholes", value: selectedSegment.potholeCount },
              { label: "Speed breakers", value: selectedSegment.speedBreakerCount },
              { label: "Rough patches", value: selectedSegment.roughPatchCount },
              { label: "Bus passes", value: selectedSegment.busPasses, strong: true },
            ];

            return (
              <>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Segment {selectedSegment.id}
                    </p>
                    <h3 className="truncate text-base font-semibold tracking-tight text-foreground">
                      {selectedSegment.name}
                    </h3>
                  </div>
                  <span
                    className="inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-semibold"
                    style={{ background: `${meta.color}1a`, color: meta.color }}
                  >
                    {meta.label}
                  </span>
                </div>

                <div
                  className="mt-4 flex items-center justify-between rounded-lg px-3 py-2.5"
                  style={{ background: `${meta.color}18` }}
                >
                  <span className="text-sm font-medium text-foreground">
                    Overall condition
                  </span>
                  <span
                    className="text-sm font-semibold"
                    style={{ color: meta.color }}
                  >
                    {meta.label} ({selectedSegment.conditionScore}/100)
                  </span>
                </div>

                <dl className="mt-4 space-y-2 border-t border-border pt-4">
                  {rows.map((r) => (
                    <div
                      key={r.label}
                      className="flex items-center justify-between"
                    >
                      <dt
                        className={`text-sm ${
                          r.strong
                            ? "font-medium text-foreground"
                            : "text-muted-foreground"
                        }`}
                      >
                        {r.label}
                      </dt>
                      <dd className="text-sm font-semibold tabular-nums text-foreground">
                        {r.value}
                      </dd>
                    </div>
                  ))}
                </dl>

                <div className="mt-4 border-t border-border pt-4">
                  <Meter
                    label="Detection confidence"
                    value={Math.round(selectedSegment.confidence * 100)}
                  />
                </div>
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
}

function Meter({
  label,
  value,
  color = "var(--foreground)",
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-xs font-semibold tabular-nums text-foreground">
          {value}%
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.min(100, Math.max(0, value))}%`, background: color }}
        />
      </div>
    </div>
  );
}
