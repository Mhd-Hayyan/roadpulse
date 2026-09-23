"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import dynamic from "next/dynamic";
import { getRoadEvents, getRoadSegments } from "@/lib/data";
import type { RoadEvent, RoadSegment, EventType } from "@/lib/types";

// Dynamic import of Leaflet map with SSR disabled to prevent 'window is not defined'
const RoadMap = dynamic(() => import("@/components/RoadMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[460px] bg-slate-100 dark:bg-slate-800 rounded-xl flex items-center justify-center text-slate-500">
      <div className="flex flex-col items-center gap-2">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-sm">Loading interactive map...</span>
      </div>
    </div>
  ),
});

export default function DashboardPage() {
  const [segments, setSegments] = useState<RoadSegment[]>([]);
  const [events, setEvents] = useState<RoadEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedEventType, setSelectedEventType] = useState<EventType | "all">("all");
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | "all">("all");

  // Fetch real data strictly from FastAPI backend
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [fetchedSegments, fetchedEvents] = await Promise.all([
        getRoadSegments(),
        getRoadEvents(),
      ]);
      setSegments(fetchedSegments);
      setEvents(fetchedEvents);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to connect to backend";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filter events based on UI selection
  const filteredEvents = useMemo(() => {
    let result = events;
    if (selectedEventType !== "all") {
      result = result.filter((e) => e.event_type === selectedEventType);
    }
    if (selectedSegmentId !== "all") {
      result = result.filter((e) => e.road_segment_id === selectedSegmentId);
    }
    return result;
  }, [events, selectedEventType, selectedSegmentId]);

  // Real KPI metrics calculated exclusively from API data
  const metrics = useMemo(() => {
    const totalSegments = segments.length;
    const totalEvents = events.length;
    const potholesCount = events.filter((e) => e.event_type === "pothole").length;
    const speedBreakersCount = events.filter((e) => e.event_type === "speed_breaker").length;
    const roughPatchesCount = events.filter((e) => e.event_type === "rough_patch").length;

    // Bus passes from segments
    const maxPasses = segments.reduce((max, s) => {
      const p = s.unique_pass_count ?? s.busPasses ?? 0;
      return p > max ? p : max;
    }, 0);

    // High or critical severity segments
    const highOrCriticalSegments = segments.filter(
      (s) => s.severity_label === "critical" || s.severity_label === "high"
    ).length;

    return {
      totalSegments,
      totalEvents,
      potholesCount,
      speedBreakersCount,
      roughPatchesCount,
      maxPasses,
      highOrCriticalSegments,
    };
  }, [segments, events]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans">
      {/* Top Navigation / Header */}
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-lg shadow-sm">
                R
              </div>
              <h1 className="text-xl font-bold tracking-tight">ROADPULSE</h1>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Bus Fleet as a Mobile Road-Condition Sensing Network
            </p>
          </div>

          {/* Connection Status Badge */}
          <div className="flex items-center gap-3">
            {error ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-100 dark:bg-red-950/70 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-xs font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse"></span>
                <span>BACKEND DISCONNECTED</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-100 dark:bg-emerald-950/70 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 text-xs font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>LIVE API</span>
              </div>
            )}

            <button
              onClick={loadData}
              disabled={loading}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 transition-colors flex items-center gap-1.5 border border-slate-200 dark:border-slate-700 disabled:opacity-50"
              title="Refresh API Data"
            >
              <svg
                className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full space-y-6">
        {/* Error State — Strict Backend Disconnected screen (NO mock fallback) */}
        {error ? (
          <div className="rounded-2xl border-2 border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30 p-8 text-center max-w-2xl mx-auto my-12 shadow-md">
            <div className="w-14 h-14 mx-auto rounded-full bg-red-100 dark:bg-red-900/60 flex items-center justify-center text-red-600 dark:text-red-400 mb-4">
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-red-900 dark:text-red-200 mb-2">
              Backend Disconnected
            </h2>
            <p className="text-sm text-red-700 dark:text-red-300 max-w-md mx-auto mb-4">
              Could not connect to the ROADPULSE FastAPI backend at{" "}
              <code className="bg-red-200/60 dark:bg-red-900/60 px-1.5 py-0.5 rounded font-mono">
                http://localhost:8000
              </code>
              . Mock fallback is disabled to ensure all data is verified against real sensor pipeline outputs.
            </p>
            <div className="bg-white dark:bg-slate-900 rounded-lg p-3 max-w-md mx-auto mb-6 text-left border border-red-200 dark:border-red-800 text-xs font-mono text-slate-700 dark:text-slate-300">
              <span className="text-slate-400 block mb-1"># Start backend with:</span>
              <span>uvicorn src.api.main:app --reload --port 8000</span>
            </div>
            <button
              onClick={loadData}
              className="px-6 py-2.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium text-sm transition-colors shadow-sm inline-flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              <span>Retry Connection</span>
            </button>
          </div>
        ) : (
          <>
            {/* KPI Metrics Cards (calculated strictly from API responses) */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3.5">
              <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                  Monitored Segments
                </div>
                <div className="text-2xl font-bold mt-1 text-slate-900 dark:text-white">
                  {metrics.totalSegments}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Kerala Corridor</div>
              </div>

              <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                  Total Detections
                </div>
                <div className="text-2xl font-bold mt-1 text-blue-600 dark:text-blue-400">
                  {metrics.totalEvents}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Across {metrics.maxPasses} Bus Passes
                </div>
              </div>

              <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                  Potholes
                </div>
                <div className="text-2xl font-bold mt-1 text-red-600 dark:text-red-400">
                  {metrics.potholesCount}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Vertical shock impacts</div>
              </div>

              <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                  Speed Breakers
                </div>
                <div className="text-2xl font-bold mt-1 text-amber-600 dark:text-amber-400">
                  {metrics.speedBreakersCount}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Pitch &amp; vertical swings</div>
              </div>

              <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                  Rough Patches
                </div>
                <div className="text-2xl font-bold mt-1 text-cyan-600 dark:text-cyan-400">
                  {metrics.roughPatchesCount}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Sustained vibrations</div>
              </div>

              <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                  High / Critical
                </div>
                <div className="text-2xl font-bold mt-1 text-rose-600 dark:text-rose-400">
                  {metrics.highOrCriticalSegments}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Priority road repairs</div>
              </div>
            </div>

            {/* Filter Bar */}
            <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
              {/* Event Type Filter Pills */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mr-1">
                  Filter:
                </span>
                <button
                  onClick={() => setSelectedEventType("all")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    selectedEventType === "all"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                  }`}
                >
                  All Events ({events.length})
                </button>
                <button
                  onClick={() => setSelectedEventType("pothole")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                    selectedEventType === "pothole"
                      ? "bg-red-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                  }`}
                >
                  <span className="w-2 h-2 rounded-full bg-red-400"></span>
                  Potholes ({metrics.potholesCount})
                </button>
                <button
                  onClick={() => setSelectedEventType("speed_breaker")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                    selectedEventType === "speed_breaker"
                      ? "bg-amber-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                  }`}
                >
                  <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                  Speed Breakers ({metrics.speedBreakersCount})
                </button>
                <button
                  onClick={() => setSelectedEventType("rough_patch")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                    selectedEventType === "rough_patch"
                      ? "bg-cyan-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                  }`}
                >
                  <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                  Rough Patches ({metrics.roughPatchesCount})
                </button>
              </div>

              {/* Segment Dropdown */}
              <div className="flex items-center gap-2">
                <label
                  htmlFor="segment-select"
                  className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider"
                >
                  Segment:
                </label>
                <select
                  id="segment-select"
                  value={selectedSegmentId}
                  onChange={(e) => setSelectedSegmentId(e.target.value)}
                  className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs rounded-lg px-3 py-1.5 font-medium focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="all">All Segments ({segments.length})</option>
                  {segments.map((seg) => (
                    <option key={seg.road_segment_id || seg.id} value={seg.road_segment_id || seg.id}>
                      {seg.road_segment_id || seg.id} ({seg.primary_condition?.replace("_", " ") || "mixed"})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Map & Event Cards Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Interactive Map (2 Columns) */}
              <div className="lg:col-span-2 h-[480px]">
                <RoadMap events={filteredEvents} selectedSegmentId={selectedSegmentId} />
              </div>

              {/* Filtered Events List (1 Column) */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-4 h-[480px] flex flex-col">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                  <h3 className="text-sm font-bold">Detected Events</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-semibold">
                    {filteredEvents.length} shown
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto space-y-2.5 mt-3 pr-1">
                  {filteredEvents.length === 0 ? (
                    <div className="text-center text-xs text-slate-400 py-12">
                      No events match current filter.
                    </div>
                  ) : (
                    filteredEvents.map((evt) => (
                      <div
                        key={evt.event_id}
                        className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 text-xs space-y-1 hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold">{evt.event_id}</span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                              evt.event_type === "pothole"
                                ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
                                : evt.event_type === "speed_breaker"
                                ? "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                                : "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                            }`}
                          >
                            {evt.event_type.replace("_", " ")}
                          </span>
                        </div>
                        <div className="flex justify-between text-slate-500 dark:text-slate-400 text-[11px]">
                          <span>Segment: <strong className="font-mono text-slate-700 dark:text-slate-200">{evt.road_segment_id}</strong></span>
                          <span>Pass #{evt.pass_id}</span>
                        </div>
                        <div className="flex justify-between text-slate-400 text-[11px]">
                          <span>Duration: {evt.duration?.toFixed(2)}s</span>
                          <span className="font-mono">{evt.latitude.toFixed(4)}, {evt.longitude.toFixed(4)}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Scored Road Segments Table (Segment-level severity & confidence from real API) */}
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
              <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold">Scored Road Segments</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Aggregated multi-pass road condition severity and confidence scoring (M11 output)
                  </p>
                </div>
                <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800">
                  {segments.length} segments analyzed
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
                    <tr>
                      <th className="px-4 py-3">Segment ID</th>
                      <th className="px-4 py-3">Primary Condition</th>
                      <th className="px-4 py-3">Health Score</th>
                      <th className="px-4 py-3">Severity</th>
                      <th className="px-4 py-3">Confidence</th>
                      <th className="px-4 py-3">Event Breakdown</th>
                      <th className="px-4 py-3">Fleet Passes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {segments.map((seg) => {
                      const segId = seg.road_segment_id || seg.id;
                      const sevLabel = seg.severity_label || "low";
                      const confLabel = seg.confidence_label || "moderate";
                      const primary = seg.primary_condition || "none";
                      const conditionScore = seg.conditionScore ?? Math.max(0, 100 - (seg.severity_score ?? 0));

                      return (
                        <tr
                          key={segId}
                          onClick={() => setSelectedSegmentId(selectedSegmentId === segId ? "all" : segId)}
                          className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/50 cursor-pointer transition-colors ${
                            selectedSegmentId === segId ? "bg-blue-50/60 dark:bg-blue-950/40" : ""
                          }`}
                        >
                          <td className="px-4 py-3 font-mono font-bold text-slate-800 dark:text-slate-200">
                            {segId}
                          </td>
                          <td className="px-4 py-3">
                            <span className="font-semibold capitalize text-slate-700 dark:text-slate-300">
                              {primary.replace("_", " ")}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-20 bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                                <div
                                  className={`h-full ${
                                    conditionScore < 40
                                      ? "bg-red-500"
                                      : conditionScore < 70
                                      ? "bg-amber-500"
                                      : "bg-emerald-500"
                                  }`}
                                  style={{ width: `${Math.min(100, Math.max(0, conditionScore))}%` }}
                                ></div>
                              </div>
                              <span className="font-mono font-bold text-xs">
                                {conditionScore.toFixed(0)}/100
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider ${
                                sevLabel === "critical"
                                  ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
                                  : sevLabel === "high"
                                  ? "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300"
                                  : sevLabel === "moderate"
                                  ? "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                                  : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                              }`}
                            >
                              {sevLabel} ({seg.severity_score?.toFixed(1) ?? 0}%)
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                                confLabel.includes("high")
                                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                                  : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                              }`}
                            >
                              {confLabel.replace("_", " ")} ({seg.confidence_percent?.toFixed(0) ?? 0}%)
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                            <span className="text-red-600 font-semibold">{seg.pothole_count ?? seg.potholeCount ?? 0}P</span>
                            {" · "}
                            <span className="text-amber-600 font-semibold">{seg.speed_breaker_count ?? seg.speedBreakerCount ?? 0}SB</span>
                            {" · "}
                            <span className="text-cyan-600 font-semibold">{seg.rough_road_count ?? seg.roughPatchCount ?? 0}RP</span>
                          </td>
                          <td className="px-4 py-3 font-semibold text-slate-700 dark:text-slate-300">
                            {seg.unique_pass_count ?? seg.busPasses ?? 0} passes
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 py-3 text-center text-xs text-slate-400">
        ROADPULSE &copy; 2026 — Bus Fleet Road Sensing &amp; Maintenance Intelligence
      </footer>
    </div>
  );
}
