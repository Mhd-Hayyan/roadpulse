"use client";

import React from "react";
import type { RoadSegment } from "@/lib/types";

interface SegmentTableProps {
  segments: RoadSegment[];
  selectedSegmentId: string | null;
  onSelectSegment: (segment: RoadSegment) => void;
}

function getSeverityBadgeClass(label?: string): string {
  switch (label) {
    case "critical":
      return "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20";
    case "high":
      return "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20";
    case "moderate":
      return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
    default:
      return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
  }
}

function getConfidenceBadgeClass(label?: string): string {
  if (label?.includes("high")) {
    return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
  }
  if (label?.includes("moderate")) {
    return "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20";
  }
  return "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20";
}

export default function SegmentTable({
  segments,
  selectedSegmentId,
  onSelectSegment,
}: SegmentTableProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b border-border px-4 py-3 bg-secondary/30">
        <div>
          <h3 className="text-sm font-bold tracking-tight text-card-foreground">
            Scored Road Segments (M11 Aggregation)
          </h3>
          <p className="text-xs text-muted-foreground">
            Prototype multi-pass severity and confidence scores computed from bus fleet sensing data
          </p>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-secondary text-foreground border border-border">
          {segments.length} segments analyzed
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-border bg-secondary/50 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-2.5">Segment</th>
              <th className="px-4 py-2.5">Primary Condition</th>
              <th className="px-4 py-2.5">Severity (M11)</th>
              <th className="px-4 py-2.5">Confidence</th>
              <th className="px-4 py-2.5">Total Events</th>
              <th className="px-4 py-2.5">Passes</th>
              <th className="px-4 py-2.5 text-center">Potholes</th>
              <th className="px-4 py-2.5 text-center">Speed Breakers</th>
              <th className="px-4 py-2.5 text-center">Rough Patches</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {segments.map((seg) => {
              const segId = seg.road_segment_id || seg.id;
              const isSelected = selectedSegmentId === segId;
              const sevScore = seg.severity_score ?? 0;
              const sevLabel = seg.severity_label ?? "low";
              const confLabel = seg.confidence_label ?? "moderate";
              const confPct = seg.confidence_percent ?? (seg.confidence ? seg.confidence * 100 : 0);
              const primary = (seg.primary_condition || "none").replace("_", " ");

              return (
                <tr
                  key={segId}
                  onClick={() => onSelectSegment(seg)}
                  className={`cursor-pointer transition-colors hover:bg-secondary/60 ${
                    isSelected ? "bg-secondary font-medium" : ""
                  }`}
                >
                  <td className="px-4 py-2.5 font-mono font-bold text-foreground">
                    {segId}
                  </td>
                  <td className="px-4 py-2.5 capitalize text-foreground">
                    {primary}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${getSeverityBadgeClass(
                        sevLabel
                      )}`}
                    >
                      {sevLabel} ({sevScore.toFixed(1)}%)
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold capitalize ${getConfidenceBadgeClass(
                        confLabel
                      )}`}
                    >
                      {confLabel.replace("_", " ")} ({confPct.toFixed(0)}%)
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-bold tabular-nums text-foreground">
                    {seg.total_event_count ?? seg.eventCount ?? 0}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-muted-foreground">
                    {seg.unique_pass_count ?? seg.busPasses ?? 0} passes
                  </td>
                  <td className="px-4 py-2.5 text-center tabular-nums font-semibold text-red-600 dark:text-red-400">
                    {seg.pothole_count ?? seg.potholeCount ?? 0}
                  </td>
                  <td className="px-4 py-2.5 text-center tabular-nums font-semibold text-amber-600 dark:text-amber-400">
                    {seg.speed_breaker_count ?? seg.speedBreakerCount ?? 0}
                  </td>
                  <td className="px-4 py-2.5 text-center tabular-nums font-semibold text-blue-600 dark:text-blue-400">
                    {seg.rough_road_count ?? seg.roughPatchCount ?? 0}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
