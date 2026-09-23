"use client";

import React from "react";

interface HeaderProps {
  theme: "dark" | "light";
  onToggleTheme: () => void;
}

export default function Header({ theme, onToggleTheme }: HeaderProps) {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-border bg-background px-5 py-3 transition-colors select-none z-30 shrink-0">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-foreground text-background shadow-xs">
          <svg
            viewBox="0 0 24 24"
            className="h-4.5 w-4.5"
            fill="none"
            stroke="currentColor"
            aria-hidden
          >
            <path
              d="M4 18c2-9 14-9 16 0"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <path d="M12 4v3M12 20v.01" strokeWidth="2" strokeLinecap="round" />
            <circle cx="12" cy="13" r="1.6" fill="currentColor" stroke="none" />
          </svg>
        </div>
        <span className="shrink-0 text-[15px] font-semibold tracking-tight text-foreground">
          RoadPulse
        </span>
        <span className="mx-1 hidden h-5 w-px shrink-0 bg-border sm:block" />
        <div className="hidden min-w-0 sm:block">
          <p className="truncate text-sm font-medium text-foreground">
            NH66 — Kochi → Thiruvananthapuram{" "}
            <span className="text-xs text-muted-foreground font-normal">
              (Kerala Coastal Corridor)
            </span>
          </p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2.5">
        <div className="flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--rp-healthy)] opacity-60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[var(--rp-healthy)]" />
          </span>
          <span className="text-xs font-medium text-muted-foreground">
            Live sensing
          </span>
        </div>

        <button
          type="button"
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        >
          {theme === "dark" ? (
            <svg
              viewBox="0 0 24 24"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden
            >
              <circle cx="12" cy="12" r="4" />
              <path
                d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
                strokeLinecap="round"
              />
            </svg>
          ) : (
            <svg
              viewBox="0 0 24 24"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden
            >
              <path
                d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </button>
      </div>
    </header>
  );
}
