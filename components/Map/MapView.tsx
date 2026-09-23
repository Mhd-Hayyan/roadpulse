"use client";

import React, { useEffect, useMemo } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import type { RoadEvent, RoadSegment, EventType } from "@/lib/types";

// Helper component to auto-fit bounds on load and when events change
function MapBoundsFitter({ positions }: { positions: [number, number][] }) {
  const map = useMap();

  useEffect(() => {
    if (positions.length > 0) {
      const bounds = L.latLngBounds(positions);
      map.fitBounds(bounds, { padding: [48, 48], maxZoom: 16 });
    } else {
      // Default to Kochi sensing corridor bounds
      map.setView([9.934, 76.270], 14);
    }
  }, [map, positions]);

  return null;
}

const GLYPH_SVG: Record<EventType, string> = {
  pothole:
    '<circle cx="12" cy="12" r="6" fill="white" opacity="0.3"/><circle cx="12" cy="12" r="2.8" fill="white"/>',
  speed_breaker:
    '<path d="M4 15c3-7 13-7 16 0" fill="none" stroke="white" stroke-width="3" stroke-linecap="round"/><path d="M4 15h16" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-dasharray="2 2.5"/>',
  rough_patch:
    '<path d="M3 13l4-4 4 4 4-4 4 4" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
};

function getMarkerColor(type: EventType): string {
  if (type === "pothole") return "#dc2626"; // Red
  if (type === "speed_breaker") return "#d97706"; // Amber
  return "#2563eb"; // Blue
}

function getEventCoordinates(event: RoadEvent): [number, number] | null {
  const lat =
    typeof event.map_match_latitude === "number" && event.map_match_latitude !== 0
      ? event.map_match_latitude
      : typeof event.center_latitude === "number" && event.center_latitude !== 0
      ? event.center_latitude
      : event.latitude;

  const lon =
    typeof event.map_match_longitude === "number" && event.map_match_longitude !== 0
      ? event.map_match_longitude
      : typeof event.center_longitude === "number" && event.center_longitude !== 0
      ? event.center_longitude
      : event.longitude;

  if (
    typeof lat === "number" &&
    !isNaN(lat) &&
    typeof lon === "number" &&
    !isNaN(lon) &&
    lat !== 0 &&
    lon !== 0
  ) {
    return [lat, lon];
  }
  return null;
}

function createMarkerIcon(event: RoadEvent, selected: boolean) {
  const color = getMarkerColor(event.event_type);
  const size = selected ? 26 : 20;

  return L.divIcon({
    className: "custom-leaflet-marker",
    html: `
      <div class="rp-marker${selected ? " rp-marker--selected" : ""}" style="
        width: ${size}px;
        height: ${size}px;
        background: ${color};
        border-radius: 9999px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.35);
        border: 2px solid #ffffff;
        cursor: pointer;
        transform: translate(-${size / 2}px, -${size / 2}px);
      ">
        <svg viewBox="0 0 24 24" style="width: 13px; height: 13px; color: #ffffff;">
          ${GLYPH_SVG[event.event_type]}
        </svg>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

interface MapViewProps {
  events: RoadEvent[];
  segments: RoadSegment[];
  selectedEventId: string | null;
  selectedSegmentId: string | null;
  onSelectEvent: (event: RoadEvent) => void;
  onSelectSegment?: (segment: RoadSegment) => void;
}

export default function MapView({
  events,
  selectedEventId,
  selectedSegmentId,
  onSelectEvent,
}: MapViewProps) {
  // Filter events if a specific segment is selected
  const visibleEvents = useMemo(() => {
    if (!selectedSegmentId || selectedSegmentId === "all") {
      return events;
    }
    return events.filter(
      (e) => e.road_segment_id === selectedSegmentId || (e as { segmentId?: string }).segmentId === selectedSegmentId
    );
  }, [events, selectedSegmentId]);

  // Extract valid real coordinates for all visible events
  const eventCoordPairs = useMemo(() => {
    return visibleEvents
      .map((e) => ({ event: e, coords: getEventCoordinates(e) }))
      .filter((item): item is { event: RoadEvent; coords: [number, number] } => item.coords !== null);
  }, [visibleEvents]);

  const allPositions = useMemo(() => {
    return eventCoordPairs.map((p) => p.coords);
  }, [eventCoordPairs]);

  // Sensed route trace polyline (ordered by pass and time sequence)
  const routePolylineCoords = useMemo<[number, number][]>(() => {
    const sorted = [...eventCoordPairs].sort((a, b) => {
      const passA = a.event.pass_id ?? 1;
      const passB = b.event.pass_id ?? 1;
      if (passA !== passB) return passA - passB;
      return (a.event.start_time ?? 0) - (b.event.start_time ?? 0);
    });
    return sorted.map((p) => p.coords);
  }, [eventCoordPairs]);

  const defaultCenter: [number, number] = [9.934, 76.270];
  const center: [number, number] = allPositions.length > 0 ? allPositions[0] : defaultCenter;

  return (
    <div className="relative w-full h-full bg-background select-none">
      <MapContainer
        center={center}
        zoom={14}
        zoomControl={false}
        scrollWheelZoom={true}
        className="w-full h-full z-10"
        preferCanvas
      >
        <MapBoundsFitter positions={allPositions} />

        {/* High-contrast / charcoal basemap tiles styled via CSS */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        {/* SENSED ROUTE TRACE (Truthfully derived from actual event coordinates, not fake geometry) */}
        {routePolylineCoords.length > 1 && (
          <Polyline
            positions={routePolylineCoords}
            pathOptions={{
              color: "#3b82f6",
              weight: 3.5,
              opacity: 0.7,
              dashArray: "6, 8",
              lineCap: "round",
              lineJoin: "round",
            }}
          />
        )}

        {/* REAL EVENT MARKERS (Positioned strictly with real API coordinates) */}
        {eventCoordPairs.map(({ event, coords }) => {
          const isSelected = selectedEventId === event.event_id;
          const icon = createMarkerIcon(event, isSelected);

          return (
            <Marker
              key={event.event_id}
              position={coords}
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
