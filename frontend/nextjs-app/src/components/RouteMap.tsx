"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface RouteMapProps {
  geometry: {
    coordinates: [number, number][]; // [lng, lat]
  };
  trailName: string;
}

export default function RouteMap({ geometry, trailName }: RouteMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || !geometry?.coordinates?.length) return;

    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const coords: [number, number][] = geometry.coordinates.map((c) => [c[1], c[0]]);
    const map = L.map(mapRef.current).setView(coords[0], 13);
    mapInstanceRef.current = map;

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
    }).addTo(map);

    const polyline = L.polyline(coords, { color: "#22c55e", weight: 4 }).addTo(map);
    map.fitBounds(polyline.getBounds(), { padding: [20, 20] });

    return () => { map.remove(); mapInstanceRef.current = null; };
  }, [geometry]);

  return <div ref={mapRef} style={{ width: "100%", height: "100%" }} />;
}
