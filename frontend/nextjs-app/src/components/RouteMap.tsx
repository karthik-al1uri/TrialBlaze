"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface Coordinate {
  0: number; // lng
  1: number; // lat
}

interface RouteMapProps {
  geometry: {
    coordinates: Coordinate[];
    elevation_profile?: { distance_mi: number; elev_ft: number }[];
  };
  trailName: string;
}

export default function RouteMap({ geometry, trailName }: RouteMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || !geometry?.coordinates?.length) return;

    // Cleanup previous map instance
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const coords: [number, number][] = geometry.coordinates.map(
      (c) => [c[1], c[0]] as [number, number]
    );
    if (!coords.length) return;

    const map = L.map(mapRef.current).setView(coords[0], 13);
    mapInstanceRef.current = map;

    L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenTopoMap",
      maxZoom: 17,
    }).addTo(map);

    const polyline = L.polyline(coords, {
      color: "#22c55e",
      weight: 4,
      opacity: 0.9,
    }).addTo(map);

    map.fitBounds(polyline.getBounds(), { padding: [20, 20] });

    // Start marker
    L.circleMarker(coords[0], {
      radius: 8,
      color: "#22c55e",
      fillColor: "#22c55e",
      fillOpacity: 1,
    })
      .bindPopup("Start")
      .addTo(map);

    // End marker
    L.circleMarker(coords[coords.length - 1], {
      radius: 8,
      color: "#ef4444",
      fillColor: "#ef4444",
      fillOpacity: 1,
    })
      .bindPopup("End")
      .addTo(map);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, [geometry, trailName]);

  return <div ref={mapRef} style={{ width: "100%", height: "100%" }} />;
}
