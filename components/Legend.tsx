"use client";

import React from "react";

const ORDER = [
  { label: "Healthy", color: "#16a34a" },
  { label: "Warning", color: "#d97706" },
  { label: "Severe", color: "#dc2626" },
];

export default function Legend() {
  return (
    <div className="flex items-center gap-3 rounded-full border border-border bg-background/90 px-3 py-1.5 shadow-sm backdrop-blur select-none">
      {ORDER.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5">
          <span
            className="h-1 w-3.5 rounded-full shadow-2xs"
            style={{ background: item.color }}
          />
          <span className="text-[11px] font-medium text-muted-foreground">
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
}
