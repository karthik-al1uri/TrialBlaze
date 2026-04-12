"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import L from "leaflet";
import "leaflet.markercluster";
import { Loader2 } from "lucide-react";
import {
  fetchGeometry,
  type TrailReference,
  type MapTrail,
} from "@/lib/api";

const CO_CENTER: [number, number] = [39.55, -105.78];
const CO_ZOOM = 7;

function getDiffColor(d?: string) {
  switch (d) {
    case "easy": return "#22c55e";
    case "moderate": return "#f59e0b";
    case "hard": return "#ef4444";
    default: return "#6b7280";
  }
}

const PIN_COLOR = "#059669";   // emerald-600
const PIN_BORDER = "#047857"; // emerald-700

function createTrailIcon() {
  return L.divIcon({
    html: `
      <svg width="24" height="32" viewBox="0 0 24 32" style="filter:drop-shadow(0 2px 3px rgba(0,0,0,0.3))">
        <path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 20 12 20s12-11 12-20C24 5.4 18.6 0 12 0z"
              fill="${PIN_COLOR}" stroke="${PIN_BORDER}" stroke-width="1"/>
        <circle cx="12" cy="11" r="4.5" fill="white" opacity="0.9"/>
      </svg>
    `,
    className: "custom-trail-icon",
    iconSize: [24, 32],
    iconAnchor: [12, 32],
    popupAnchor: [0, -32],
  });
}

function makeSelectedIcon() {
  return L.divIcon({
    className: "",
    iconSize: [32, 42],
    iconAnchor: [16, 42],
    popupAnchor: [0, -44],
    html: `<div style="filter:drop-shadow(0 3px 6px rgba(0,0,0,0.4));cursor:pointer;animation:bounce 0.3s ease-out;">
      <svg width="32" height="42" viewBox="0 0 32 42">
        <path d="M16 0C7.2 0 0 7.2 0 16c0 12 16 26 16 26s16-14 16-26C32 7.2 24.8 0 16 0z"
              fill="#0d9488" stroke="white" stroke-width="2.5"/>
        <circle cx="16" cy="14" r="6" fill="white" opacity="0.95"/>
        <circle cx="16" cy="14" r="2.5" fill="#0d9488"/>
      </svg>
    </div>`,
  });
}

function makeClusterIcon(cluster: L.MarkerCluster) {
  const total = cluster.getChildCount();
  const size = total < 10 ? 34 : total < 50 ? 40 : 48;
  const half = size / 2;
  const fontSize = total < 100 ? 12 : 10;

  return L.divIcon({
    html: `
      <div style="cursor:pointer;transition:transform 0.15s ease;"
           onmouseover="this.style.transform='scale(1.1)'"
           onmouseout="this.style.transform='scale(1)'">
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"
             style="filter:drop-shadow(0 1px 3px rgba(0,0,0,0.25))">
          <circle cx="${half}" cy="${half}" r="${half - 1}" fill="#059669" opacity="0.9"/>
          <circle cx="${half}" cy="${half}" r="${half - 3}" fill="none" stroke="white" stroke-width="1.5" opacity="0.6"/>
          <text x="${half}" y="${half}" text-anchor="middle"
            dominant-baseline="central"
            fill="white" font-weight="700" font-size="${fontSize}"
            font-family="-apple-system,BlinkMacSystemFont,sans-serif">${total}</text>
        </svg>
      </div>
    `,
    className: "custom-cluster-icon",
    iconSize: [size, size],
    iconAnchor: [half, half],
  });
}

interface TrailMapProps {
  featuredTrails?: MapTrail[];
  selectedTrail?: MapTrail | null;
  highlightedTrails?: TrailReference[];
  onTrailClick?: (trail: MapTrail) => void;
  onClusterClick?: (trails: MapTrail[]) => void;
  mapBounds?: [[number, number], [number, number]] | null;
  isochronePolygon?: { type: string; coordinates: number[][][] } | null;
}

export default function TrailMap({
  featuredTrails = [],
  selectedTrail = null,
  highlightedTrails = [],
  onTrailClick,
  onClusterClick,
  mapBounds = null,
  isochronePolygon = null,
}: TrailMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const clusterRef = useRef<L.MarkerClusterGroup | null>(null);
  const routeLayersRef = useRef<L.Layer[]>([]);
  const selectedPinRef = useRef<L.Marker | null>(null);
  const trailByMarkerRef = useRef<Map<L.Marker, MapTrail>>(new Map());
  const layerControlRef = useRef<L.Control.Layers | null>(null);
  const isoLayerRef = useRef<L.GeoJSON | null>(null);
  const [loading, setLoading] = useState(false);
  const [mapAttribution, setMapAttribution] = useState("© OpenTopoMap contributors");

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const m = L.map(mapContainer.current, {
      center: CO_CENTER,
      zoom: CO_ZOOM,
      zoomControl: true,
      scrollWheelZoom: true,
      zoomAnimation: true,
      markerZoomAnimation: true,
    });
    // Base layers — Topo is default
    const streetLayer = L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { attribution: "© OpenStreetMap contributors", maxZoom: 19 }
    );
    const topoLayer = L.tileLayer(
      "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
      { attribution: "© OpenTopoMap contributors", maxZoom: 17 }
    );
    topoLayer.addTo(m); // DEFAULT layer
    const satelliteLayer = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { attribution: "© ESRI World Imagery", maxZoom: 19 }
    );
    const usgsTopo = L.tileLayer(
      "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
      { attribution: "© USGS National Map", maxZoom: 16 }
    );

    // Optional Mapbox GL JS satellite layer (only when token is set)
    const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
    const mapboxLayer = mapboxToken
      ? L.tileLayer(
          `https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v12/tiles/{z}/{x}/{y}@2x?access_token=${mapboxToken}`,
          {
            attribution: "© Mapbox © OpenStreetMap",
            maxZoom: 22,
            tileSize: 512,
            zoomOffset: -1,
          }
        )
      : null;

    // Overlay — hiking routes
    const hikingRoutes = L.tileLayer(
      "https://tile.waymarkedtrails.org/hiking/{z}/{x}/{y}.png",
      { attribution: "© WaymarkedTrails", opacity: 0.7 }
    );
    hikingRoutes.addTo(m); // ON by default

    // 3D Terrain — hillshade overlay from Stamen/Stadia
    const terrainHillshade = L.tileLayer(
      "https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png",
      { attribution: "© Stadia Maps / Stamen", opacity: 0.5, maxZoom: 18 }
    );

    // Fire Risk — NIFC Active Fire Perimeters WMS
    const fireRisk = (L as any).tileLayer.wms(
      "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/NIFC_Perimeters_YearToDate/FeatureServer/0/query",
      {
        layers: "0",
        format: "image/png",
        transparent: true,
        attribution: "© NIFC",
        opacity: 0.6,
      }
    );

    // Avalanche Zones — CAIC avalanche forecast zones overlay
    const avalancheZones = L.tileLayer(
      "https://tiles.stadiamaps.com/tiles/stamen_toner_lines/{z}/{x}/{y}{r}.png",
      { attribution: "© Stadia Maps", opacity: 0.3, maxZoom: 18 }
    );

    // Layer control (Trail Pins overlay added later when cluster is created)
    const baseLayers: Record<string, L.TileLayer> = {
      "Street": streetLayer,
      "Topo": topoLayer,
      "Satellite": satelliteLayer,
      "USGS Topo": usgsTopo,
    };
    if (mapboxLayer) {
      baseLayers["Mapbox Satellite"] = mapboxLayer;
    }
    const lc = L.control.layers(
      baseLayers,
      {
        "Hiking Routes": hikingRoutes,
        "3D Terrain": terrainHillshade,
        "🔥 Fire Risk": fireRisk,
        "🏔️ Avalanche Zones": avalancheZones,
      },
      { position: "topright", collapsed: window.innerWidth < 768 }
    ).addTo(m);
    layerControlRef.current = lc;

    // Dynamic attribution
    m.on("baselayerchange", (e: L.LayersControlEvent) => {
      setMapAttribution((e as any).layer?.options?.attribution || "");
    });

    mapRef.current = m;
    return () => { m.remove(); mapRef.current = null; layerControlRef.current = null; };
  }, []);

  // Respond to mapBounds prop changes (region zoom)
  useEffect(() => {
    const m = mapRef.current;
    if (!m || !mapBounds) return;
    m.fitBounds(mapBounds, { padding: [40, 40], maxZoom: 12, animate: true });
  }, [mapBounds]);

  // Draw isochrone polygon
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;

    // Remove previous isochrone layer
    if (isoLayerRef.current) {
      m.removeLayer(isoLayerRef.current);
      isoLayerRef.current = null;
    }

    if (!isochronePolygon) return;

    const geoJsonData: GeoJSON.Feature = {
      type: "Feature",
      properties: {},
      geometry: isochronePolygon as GeoJSON.Geometry,
    };

    const layer = L.geoJSON(geoJsonData, {
      style: {
        color: "#2563eb",
        weight: 2,
        opacity: 0.6,
        fillColor: "#3b82f6",
        fillOpacity: 0.15,
      },
    }).addTo(m);

    isoLayerRef.current = layer;
    m.fitBounds(layer.getBounds(), { padding: [40, 40], maxZoom: 11 });
  }, [isochronePolygon]);

  // Build cluster group with ALL trails
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;

    if (clusterRef.current) {
      m.removeLayer(clusterRef.current);
      clusterRef.current = null;
    }
    trailByMarkerRef.current.clear();
    if (featuredTrails.length === 0) return;

    const cluster = L.markerClusterGroup({
      maxClusterRadius: 55,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      disableClusteringAtZoom: 14,
      animate: true,
      animateAddingMarkers: false,
      chunkedLoading: true,
      spiderfyDistanceMultiplier: 2.5,
      iconCreateFunction: (c) => makeClusterIcon(c),
    });

    // When a cluster is clicked, show drawer for small clusters (≤5), otherwise zoom
    cluster.on("clusterclick", (e: any) => {
      const childMarkers = e.layer.getAllChildMarkers();
      const seen = new Set<string>();
      const clusterTrails: MapTrail[] = [];
      childMarkers.forEach((marker: L.Marker) => {
        const t = trailByMarkerRef.current.get(marker);
        if (t && !seen.has(t.name)) {
          seen.add(t.name);
          clusterTrails.push(t);
        }
      });
      if (childMarkers.length <= 5 && clusterTrails.length > 0) {
        e.originalEvent?.stopPropagation();
        onClusterClick?.(clusterTrails);
      } else if (clusterTrails.length > 0 && onClusterClick) {
        onClusterClick(clusterTrails);
      }
    });

    featuredTrails.forEach((trail) => {
      if (!trail.lat || !trail.lng) return;
      const color = getDiffColor(trail.difficulty);
      const marker = L.marker([trail.lat, trail.lng], {
        icon: createTrailIcon(),
        trailData: trail,
      } as any);

      // Store trail reference for cluster click
      trailByMarkerRef.current.set(marker, trail);

      // Hover tooltip
      const diffLabel = trail.difficulty ? trail.difficulty.charAt(0).toUpperCase() + trail.difficulty.slice(1) : "";
      marker.bindTooltip(
        `<div style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;min-width:120px;">
          <div style="font-size:12px;font-weight:600;color:#1e293b;margin-bottom:2px;">${trail.name}</div>
          <div style="font-size:10px;color:#64748b;display:flex;gap:6px;flex-wrap:wrap;">
            ${trail.nearby_city ? `<span>${trail.nearby_city}</span>` : ""}
            ${diffLabel ? `<span style="color:${color};font-weight:600;">${diffLabel}</span>` : ""}
            ${trail.length_miles ? `<span>${trail.length_miles} mi</span>` : ""}
          </div>
          ${trail.wildlife_alert ? `<div style="font-size:10px;color:#b91c1c;margin-top:4px;font-weight:600;">⚠️ Recent wildlife alert${trail.wildlife_alert_species?.length ? `: ${trail.wildlife_alert_species.join(", ")}` : ""}</div>` : ""}
        </div>`,
        {
          direction: "top",
          offset: [0, -34],
          className: "trail-tooltip",
          sticky: false,
        }
      );

      marker.on("click", () => onTrailClick?.(trail));
      cluster.addLayer(marker);
    });

    m.addLayer(cluster);
    clusterRef.current = cluster;

    // Add Trail Pins overlay to layer control
    if (layerControlRef.current) {
      layerControlRef.current.addOverlay(cluster, "Trail Pins");
    }

    // Crowd density heatmap — canvas circles sized by review_count
    const heatTrails = featuredTrails.filter((t) => t.lat && t.lng && (t.review_count ?? 0) > 0);
    if (heatTrails.length > 0) {
      const maxReviews = Math.max(...heatTrails.map((t) => t.review_count ?? 1), 1);
      const heatGroup = L.layerGroup(
        heatTrails.map((t) => {
          const r = Math.max(6, Math.round(((t.review_count ?? 1) / maxReviews) * 28));
          return L.circleMarker([t.lat!, t.lng!], {
            radius: r,
            color: "transparent",
            fillColor: "#f59e0b",
            fillOpacity: 0.25,
            interactive: false,
          });
        })
      );
      if (layerControlRef.current) {
        layerControlRef.current.addOverlay(heatGroup, "🔥 Crowd Density");
      }
    }

    return () => {
      // Remove overlay from layer control on cleanup
      if (layerControlRef.current && clusterRef.current) {
        layerControlRef.current.removeLayer(clusterRef.current);
      }
    };
  }, [featuredTrails, onTrailClick, onClusterClick]);

  // Highlight selected trail with special pin
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;

    if (selectedPinRef.current) {
      m.removeLayer(selectedPinRef.current);
      selectedPinRef.current = null;
    }

    if (selectedTrail?.lat && selectedTrail?.lng) {
      const pin = L.marker([selectedTrail.lat, selectedTrail.lng], {
        icon: makeSelectedIcon(),
        zIndexOffset: 2000,
      }).addTo(m);
      selectedPinRef.current = pin;

      // Pan to the selected trail
      m.setView([selectedTrail.lat, selectedTrail.lng], Math.max(m.getZoom(), 10), {
        animate: true,
        duration: 0.5,
      });
    }
  }, [selectedTrail]);

  // Draw route polyline for selected trail
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;
    routeLayersRef.current.forEach((l) => l.remove());
    routeLayersRef.current = [];

    if (!selectedTrail) return;

    setLoading(true);
    fetchGeometry([selectedTrail.name])
      .then((data) => {
        if (!mapRef.current) return;
        const trail = data.trails[0];
        if (!trail?.coordinates?.length) return;

        const color = getDiffColor(selectedTrail.difficulty);
        const latlngs: [number, number][] = trail.coordinates.map(
          (c) => [c[1], c[0]] as [number, number]
        );

        // Route outline + line
        const outline = L.polyline(latlngs, { color: "white", weight: 8, opacity: 0.6 }).addTo(m);
        const line = L.polyline(latlngs, {
          color, weight: 4, opacity: 0.95,
          lineCap: "round", lineJoin: "round",
        }).addTo(m);
        routeLayersRef.current.push(outline, line);

        // Start dot (hollow)
        if (latlngs.length > 0) {
          const s = L.circleMarker(latlngs[0], {
            radius: 7, color, fillColor: "white", fillOpacity: 1, weight: 3,
          }).addTo(m);
          routeLayersRef.current.push(s);
        }
        // End dot (filled)
        if (latlngs.length > 1) {
          const e = L.circleMarker(latlngs[latlngs.length - 1], {
            radius: 7, color: "white", fillColor: color, fillOpacity: 1, weight: 3,
          }).addTo(m);
          routeLayersRef.current.push(e);
        }

        // Fit bounds to route
        m.fitBounds(L.latLngBounds(latlngs), { padding: [60, 60], maxZoom: 15 });

        // Trailheads
        data.trailheads.forEach((th) => {
          const thm = L.marker([th.latitude, th.longitude], {
            icon: L.divIcon({
              className: "",
              iconSize: [22, 22],
              iconAnchor: [11, 11],
              html: `<div style="width:22px;height:22px;border-radius:50%;background:#1e40af;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;font-size:10px;color:white;font-weight:700;">P</div>`,
            }),
          })
            .bindPopup(`<b>${th.name}</b><br/><span style="font-size:11px;color:#64748b;">Trailhead / Parking</span>`, { closeButton: false })
            .addTo(m);
          routeLayersRef.current.push(thm);
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedTrail]);

  // Draw AI highlighted trails
  useEffect(() => {
    const m = mapRef.current;
    if (!m || selectedTrail || highlightedTrails.length === 0) return;

    routeLayersRef.current.forEach((l) => l.remove());
    routeLayersRef.current = [];

    setLoading(true);
    fetchGeometry(highlightedTrails.map((t) => t.name))
      .then((data) => {
        if (!mapRef.current) return;
        const bounds = L.latLngBounds([]);
        let hasBounds = false;

        data.trails.forEach((trail) => {
          if (!trail.coordinates?.length) return;
          const ref = highlightedTrails.find(
            (t) => t.name.toLowerCase() === trail.name.toLowerCase()
          );
          const color = getDiffColor(ref?.difficulty);
          const latlngs: [number, number][] = trail.coordinates.map(
            (c) => [c[1], c[0]] as [number, number]
          );

          const outline = L.polyline(latlngs, { color: "white", weight: 7, opacity: 0.5 }).addTo(m);
          const line = L.polyline(latlngs, { color, weight: 4, opacity: 0.9 }).addTo(m);
          routeLayersRef.current.push(outline, line);
          latlngs.forEach((ll) => { bounds.extend(ll); hasBounds = true; });
        });

        if (hasBounds) m.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [highlightedTrails, selectedTrail]);

  return (
    <div className="relative w-full h-full flex flex-col">
      <div ref={mapContainer} className="w-full flex-1" />
      <p className="text-xs text-gray-400 mt-1 px-2 select-none">
        Map tiles: {mapAttribution}
      </p>
      {loading && (
        <div className="absolute top-4 right-4 bg-white/95 backdrop-blur rounded-lg shadow-lg px-3 py-2 z-[1000] flex items-center gap-2">
          <Loader2 className="w-4 h-4 text-emerald-600 animate-spin" />
          <span className="text-sm text-gray-600">Loading trail...</span>
        </div>
      )}
      {/* Trail count overlay */}
      <div className="absolute bottom-8 left-3 bg-white/90 backdrop-blur rounded-lg shadow px-3 py-1.5 z-[1000]">
        <span className="text-[11px] text-gray-600 font-medium">
          {featuredTrails.length} trails on map
        </span>
      </div>
    </div>
  );
}
