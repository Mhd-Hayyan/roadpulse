"use client";

import React from "react";
import { EventGlyph } from "@/components/EventGlyph";

const ANOMALIES = [
  { label: "Pothole", color: "#dc2626", type: "pothole" as const },
  { label: "Speed Breaker", color: "#d97706", type: "speed_breaker" as const },
  { label: "Rough Patch", color: "#2563eb", type: "rough_patch" as const },
];

export default function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-background/95 px-3 py-2 shadow-sm backdrop-blur select-none text-xs">
      <div className="flex items-center gap-3">
        {ANOMALIES.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <span
              className="flex h-5 w-5 items-center justify-center rounded-full text-white shadow-2xs"
              style={{ background: item.color }}
            >
              <EventGlyph type={item.type} className="h-3 w-3" />
            </span>
            <span className="text-[11px] font-medium text-foreground">
              {item.label}
            </span>
          </div>
        ))}
      </div>

      <div className="hidden sm:flex items-center gap-1.5 pl-2 border-l border-border text-muted-foreground text-[11px]">
        <span className="h-0.5 w-4 border-t-2 border-dashed border-blue-500" />
        <span>Sensed Route Trace</span>
      </div>
    </div>
  );
}
