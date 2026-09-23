"use client";

import React, { Fragment, useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import type { RoadEvent, RoadSegment, EventType } from "@/lib/types";
import { getRoadSegmentGeometry } from "@/lib/data";

// Helper component to auto-fit bounds on load
function MapBoundsFitter() {
  const map = useMap();
  useEffect(() => {
    // Fits the map tightly to the Kochi/Ernakulam road corridor bounding box
    const bounds = L.latLngBounds([
      [9.952, 76.270], // South-West (MG Road South)
      [10.020, 76.370], // North-East (Kakkanad Infopark / Edappally)
    ]);
    map.fitBounds(bounds, { padding: [32, 32] });
  }, [map]);
  return null;
}

const GLYPH: Record<EventType, string> = {
  pothole:
    '<circle cx="12" cy="12" r="6" fill="white"/><circle cx="12" cy="12" r="2.5" fill="currentColor"/>',
  speed_breaker:
    '<path d="M4 15c3-7 13-7 16 0" fill="none" stroke="white" stroke-width="3" stroke-linecap="round"/><path d="M4 15h16" stroke="white" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="2 2.5"/>',
  rough_patch:
    '<path d="M3 13l4-4 4 4 4-4 4 4" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
};

function getConditionColor(severity: number): string {
  if (severity >= 66) return "#dc2626"; // Severe
  if (severity >= 33) return "#d97706"; // Warning
  return "#16a34a"; // Healthy
}

function getSegmentColor(score: number): string {
  if (score >= 75) return "#16a34a"; // Healthy
  if (score >= 50) return "#d97706"; // Warning
  return "#dc2626"; // Severe
}

function createMarkerIcon(event: RoadEvent, selected: boolean) {
  const color = getConditionColor(event.severity);
  const size = 16;
  return L.divIcon({
    className: "",
    html: `<div class="rp-marker${selected ? " rp-marker--selected" : ""}" style="width:${size}px;height:${size}px;background:${color};color:${color};cursor:pointer">
      <svg viewBox="0 0 24 24" style="color:#fff">${GLYPH[event.event_type]}</svg>
    </div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

interface MapViewProps {
  events: RoadEvent[];
  segments: RoadSegment[];
  selectedEventId: string | null;
  selectedSegmentId: string | null;
  showHeatmapLayer: boolean;
  onSelectEvent: (event: RoadEvent) => void;
  onSelectSegment: (segment: RoadSegment) => void;
}

export default function MapView({
  events,
  segments,
  selectedEventId,
  selectedSegmentId,
  showHeatmapLayer,
  onSelectEvent,
  onSelectSegment,
}: MapViewProps) {
  const center: [number, number] = [9.985, 76.31];

  return (
    <div className="relative w-full h-full min-h-[calc(100vh-3.5rem)] bg-background">
      <MapContainer
        center={center}
        zoom={12}
        zoomControl={false}
        scrollWheelZoom={true}
        className="w-full h-full z-10"
        preferCanvas
      >
        <MapBoundsFitter />

        {/* Standard OSM tiles styled into high-contrast / charcoal basemap via CSS */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        {/* ROAD CONDITION SEGMENT POLYLINES */}
        {segments.map((segment) => {
          const coords = getRoadSegmentGeometry(segment.id);
          if (!coords || coords.length === 0) return null;

          const isSelected = selectedSegmentId === segment.id;
          const color = getSegmentColor(segment.conditionScore);

          return (
            <Fragment key={segment.id}>
              {/* Soft underlying glow when condition overlay is active */}
              {showHeatmapLayer && (
                <Polyline
                  positions={coords}
                  pathOptions={{
                    color,
                    weight: isSelected ? 18 : 13,
                    opacity: 0.22,
                    lineCap: "round",
                    lineJoin: "round",
                  }}
                />
              )}

              {/* Solid foreground street line */}
              <Polyline
                positions={coords}
                pathOptions={{
                  color,
                  weight: isSelected ? 5.5 : 3.5,
                  opacity: 1,
                  lineCap: "round",
                  lineJoin: "round",
                }}
                eventHandlers={{
                  click: () => onSelectSegment(segment),
                }}
              />
            </Fragment>
          );
        })}

        {/* EVENT MARKERS */}
        {events.map((event) => {
          const isSelected = selectedEventId === event.event_id;
          const icon = createMarkerIcon(event, isSelected);

          return (
            <Marker
              key={event.event_id}
              position={[event.latitude, event.longitude]}
              icon={icon}
              eventHandlers={{
                click: () => onSelectEvent(event),
              }}
            />
          );
        })}
      </MapContainer>
    </div>
  );
}
