"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const CO_CENTER: [number, number] = [39.55, -105.78];
const CO_ZOOM = 7;

interface MapTrail {
  name: string;
  lat?: number;
  lng?: number;
  difficulty?: string;
}

interface TrailMapProps {
  featuredTrails?: MapTrail[];
  onTrailClick?: (trail: MapTrail) => void;
}

function getDiffColor(d?: string) {
  switch (d) {
    case "easy": return "#22c55e";
    case "moderate": return "#f59e0b";
    case "hard": return "#ef4444";
    default: return "#6b7280";
  }
}

export default function TrailMap({ featuredTrails = [], onTrailClick }: TrailMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  // Initialize map once
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const m = L.map(mapContainer.current, { center: CO_CENTER, zoom: CO_ZOOM });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
    }).addTo(m);
    mapRef.current = m;
    return () => { m.remove(); mapRef.current = null; };
  }, []);

  // Add markers when trails change
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;

    featuredTrails.forEach((trail) => {
      if (!trail.lat || !trail.lng) return;
      const color = getDiffColor(trail.difficulty);
      const marker = L.circleMarker([trail.lat, trail.lng], {
        radius: 7,
        color,
        fillColor: color,
        fillOpacity: 0.85,
        weight: 2,
      }).addTo(m);
      marker.bindTooltip(trail.name);
      marker.on("click", () => onTrailClick?.(trail));
    });
  }, [featuredTrails, onTrailClick]);

  return <div ref={mapContainer} className="w-full h-full" />;
}
