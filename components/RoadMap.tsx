"use client";

import React, { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import type { RoadEvent, EventType } from "@/lib/types";

interface RoadMapProps {
  events: RoadEvent[];
  selectedSegmentId?: string | "all";
}

/**
 * Creates custom SVG-based div icons for event markers.
 * Avoids default Leaflet icon 404 issues in Webpack/Next.js.
 */
function createEventIcon(type: EventType): L.DivIcon {
  let bgColor = "#ef4444"; // red for pothole
  let letter = "P";
  let title = "Pothole";

  if (type === "speed_breaker") {
    bgColor = "#f59e0b"; // amber for speed breaker
    letter = "S";
    title = "Speed Breaker";
  } else if (type === "rough_patch") {
    bgColor = "#3b82f6"; // blue for rough patch
    letter = "R";
    title = "Rough Patch";
  }

  const html = `
    <div style="
      background-color: ${bgColor};
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 2px 6px rgba(0,0,0,0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: 700;
      font-size: 13px;
      font-family: system-ui, sans-serif;
      cursor: pointer;
      transform: translate(-14px, -14px);
    " title="${title}">
      ${letter}
    </div>
  `;

  return L.divIcon({
    className: "custom-road-event-icon",
    html: html,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
  });
}

/**
 * Helper component to re-center the map when events change.
 */
function MapBoundsAdjuster({ positions }: { positions: [number, number][] }) {
  const map = useMap();

  useEffect(() => {
    if (positions.length > 0) {
      const bounds = L.latLngBounds(positions);
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
    }
  }, [map, positions]);

  return null;
}

export default function RoadMap({ events, selectedSegmentId }: RoadMapProps) {
  // Filter events if a specific segment is selected
  const visibleEvents = useMemo(() => {
    if (!selectedSegmentId || selectedSegmentId === "all") {
      return events;
    }
    return events.filter((e) => e.road_segment_id === selectedSegmentId);
  }, [events, selectedSegmentId]);

  // Extract coordinates for markers and route visualization
  const positions = useMemo<[number, number][]>(() => {
    return visibleEvents
      .filter((e) => typeof e.latitude === "number" && typeof e.longitude === "number")
      .map((e) => [e.latitude, e.longitude]);
  }, [visibleEvents]);

  // Fallback center in Kochi sensor corridor if no coordinates available
  const defaultCenter: [number, number] = [9.934, 76.270];
  const center: [number, number] = positions.length > 0 ? positions[0] : defaultCenter;

  return (
    <div className="w-full h-full min-h-[460px] rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 shadow-sm relative z-0">
      <MapContainer
        center={center}
        zoom={14}
        scrollWheelZoom={true}
        className="w-full h-full min-h-[460px]"
        style={{ height: "100%", width: "100%", background: "#f8fafc" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Route visualization connecting the sensed event coordinate sequence */}
        {positions.length > 1 && (
          <Polyline
            positions={positions}
            pathOptions={{
              color: "#3b82f6",
              weight: 4,
              opacity: 0.65,
              dashArray: "6, 8",
            }}
          />
        )}

        {/* Event Markers with real API fields only */}
        {visibleEvents.map((evt) => {
          if (typeof evt.latitude !== "number" || typeof evt.longitude !== "number") {
            return null;
          }

          const icon = createEventIcon(evt.event_type);

          return (
            <Marker
              key={evt.event_id}
              position={[evt.latitude, evt.longitude]}
              icon={icon}
            >
              <Popup className="roadpulse-popup">
                <div className="p-1 min-w-[200px] text-slate-800">
                  <div className="flex items-center justify-between border-b pb-1.5 mb-2">
                    <span className="font-bold font-mono text-xs text-slate-500">
                      {evt.event_id}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded font-semibold uppercase tracking-wider ${
                        evt.event_type === "pothole"
                          ? "bg-red-100 text-red-700"
                          : evt.event_type === "speed_breaker"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-blue-100 text-blue-700"
                      }`}
                    >
                      {evt.event_type.replace("_", " ")}
                    </span>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Road Segment:</span>
                      <span className="font-medium font-mono">{evt.road_segment_id}</span>
                    </div>

                    {typeof evt.pass_id === "number" && (
                      <div className="flex justify-between">
                        <span className="text-slate-500">Bus Pass:</span>
                        <span className="font-medium">Pass #{evt.pass_id}</span>
                      </div>
                    )}

                    {typeof evt.duration === "number" && (
                      <div className="flex justify-between">
                        <span className="text-slate-500">Duration:</span>
                        <span className="font-medium">{evt.duration.toFixed(2)}s</span>
                      </div>
                    )}

                    {evt.map_match_status && (
                      <div className="flex justify-between">
                        <span className="text-slate-500">Map Status:</span>
                        <span className="font-medium capitalize text-emerald-600">
                          {evt.map_match_status}
                        </span>
                      </div>
                    )}

                    <div className="flex justify-between pt-1 border-t border-slate-100 text-[11px] text-slate-400">
                      <span>Coordinates:</span>
                      <span className="font-mono">
                        {evt.latitude.toFixed(5)}, {evt.longitude.toFixed(5)}
                      </span>
                    </div>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        <MapBoundsAdjuster positions={positions} />
      </MapContainer>

      {/* Map Legend */}
      <div className="absolute bottom-4 right-4 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm px-3 py-2 rounded-lg shadow-md border border-slate-200 dark:border-slate-800 text-xs z-[1000] flex flex-col gap-1.5">
        <span className="font-semibold text-slate-700 dark:text-slate-300 border-b pb-1">
          Anomaly Types
        </span>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500 inline-block"></span>
          <span className="text-slate-600 dark:text-slate-400">Pothole</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-amber-500 inline-block"></span>
          <span className="text-slate-600 dark:text-slate-400">Speed Breaker</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-blue-500 inline-block"></span>
          <span className="text-slate-600 dark:text-slate-400">Rough Patch</span>
        </div>
        <div className="flex items-center gap-2 pt-1 border-t border-slate-100 dark:border-slate-800">
          <span className="w-3 h-0.5 border-t border-dashed border-blue-500 inline-block"></span>
          <span className="text-slate-500 text-[11px]">Bus Sensing Route</span>
        </div>
      </div>
    </div>
  );
}
