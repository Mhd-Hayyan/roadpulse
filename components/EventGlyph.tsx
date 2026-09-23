import React from "react";
import type { EventType } from "@/lib/types";

interface EventGlyphProps {
  type: EventType;
  className?: string;
}

export function EventGlyph({ type, className = "w-4 h-4" }: EventGlyphProps) {
  const common = {
    viewBox: "0 0 24 24",
    className,
    "aria-hidden": true,
  };

  if (type === "pothole") {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="7" fill="currentColor" opacity="0.2" />
        <circle cx="12" cy="12" r="3" fill="currentColor" />
      </svg>
    );
  }

  if (type === "speed_breaker") {
    return (
      <svg {...common} fill="none" stroke="currentColor">
        <path
          d="M3 15c3.5-8 14.5-8 18 0"
          strokeWidth="2.2"
          strokeLinecap="round"
        />
        <path
          d="M3 15h18"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeDasharray="1.5 2.5"
        />
      </svg>
    );
  }

  // rough_patch
  return (
    <svg {...common} fill="none" stroke="currentColor">
      <path
        d="M2 13l4-4 4 4 4-4 4 4 4-4"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
export default EventGlyph;
