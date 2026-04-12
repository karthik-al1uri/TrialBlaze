"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import ChatPanel from "@/components/ChatPanel";
import TrailCards from "@/components/TrailCards";
import TrailDetail from "@/components/TrailDetail";
import ClusterDrawer from "@/components/ClusterDrawer";
import { MessageSquare, X, Mountain, Search, Car, Loader2, Settings, Heart, Map, Moon, Sun, GitCompare, CalendarDays, Activity, Share2 } from "lucide-react";
import { fetchFeaturedTrails, fetchTrailsByRegion, fetchIsochrone, fetchSurpriseTrail, type TrailReference, type MapTrail, type IsochroneResponse } from "@/lib/api";
import TrailComparison from "@/components/TrailComparison";
import ItineraryBuilder from "@/components/ItineraryBuilder";
import ConditionsFeed from "@/components/ConditionsFeed";

const TrailMap = dynamic(() => import("@/components/TrailMap"), { ssr: false });

export default function Home() {
  const [highlightedTrails, setHighlightedTrails] = useState<TrailReference[]>([]);
  const [featuredTrails, setFeaturedTrails] = useState<MapTrail[]>([]);
  const [selectedTrail, setSelectedTrail] = useState<MapTrail | null>(null);
  const [clusterTrails, setClusterTrails] = useState<MapTrail[] | null>(null);
  const [weatherContext, setWeatherContext] = useState<string | undefined>();
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [chatOpen, setChatOpen] = useState(false);
  const [chatSeen, setChatSeen] = useState(true);
  const [filterDifficulty, setFilterDifficulty] = useState<string | undefined>();
  const [searchQuery, setSearchQuery] = useState("");
  const [drawerTrails, setDrawerTrails] = useState<MapTrail[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [mobileTab, setMobileTab] = useState<"map" | "search" | "chat" | "saved">("map");
  const [activeRegion, setActiveRegion] = useState<string | null>(null);
  const [mapBounds, setMapBounds] = useState<[[number, number], [number, number]] | null>(null);

  // Fitness profile state
  interface FitnessProfile {
    fitness_level: "beginner" | "intermediate" | "advanced";
    max_distance_miles: number;
    max_elevation_gain_ft: number;
    pace_min_per_mile: number;
    preferred_surface: "any" | "paved" | "dirt" | "gravel";
  }
  const defaultFitness: FitnessProfile = {
    fitness_level: "intermediate",
    max_distance_miles: 10,
    max_elevation_gain_ft: 2000,
    pace_min_per_mile: 30,
    preferred_surface: "any",
  };
  const [fitnessProfile, setFitnessProfile] = useState<FitnessProfile>(defaultFitness);
  const [fitnessFilterOn, setFitnessFilterOn] = useState(false);
  const [fitnessOpen, setFitnessOpen] = useState(false);

  // Favorites state
  const [favorites, setFavorites] = useState<string[]>([]);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [surpriseLoading, setSurpriseLoading] = useState(false);

  // Dark mode
  const [darkMode, setDarkMode] = useState(false);

  // Trail comparison
  const [compareTrails, setCompareTrails] = useState<MapTrail[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);

  // Itinerary builder
  const [itineraryOpen, setItineraryOpen] = useState(false);

  // Conditions feed sidebar tab
  const [conditionsOpen, setConditionsOpen] = useState(false);

  // Share toast
  const [shareToast, setShareToast] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("trailblaze_favorites");
      if (saved) setFavorites(JSON.parse(saved));
    } catch {}
    setChatSeen(!!localStorage.getItem("chat_seen"));
    // Dark mode persisted preference
    const dm = localStorage.getItem("trailblaze_dark");
    if (dm === "1") setDarkMode(true);
    // Deep-link: ?trail=Bear+Peak
    const params = new URLSearchParams(window.location.search);
    const trailParam = params.get("trail");
    if (trailParam) {
      setSelectedTrail({ name: trailParam, review_count: 0 });
    }
  }, []);

  const handleOpenChat = () => {
    setChatOpen(true);
    setChatSeen(true);
    localStorage.setItem("chat_seen", "1");
  };

  const toggleFavorite = (name: string) => {
    setFavorites((prev) => {
      const next = prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name];
      try { localStorage.setItem("trailblaze_favorites", JSON.stringify(next)); } catch {}
      return next;
    });
  };

  // Load fitness profile from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("trailblaze_fitness");
      if (saved) {
        const parsed = JSON.parse(saved);
        setFitnessProfile({ ...defaultFitness, ...parsed });
        if (parsed._filterOn) setFitnessFilterOn(true);
      }
    } catch {}
  }, []);

  const updateFitness = (updates: Partial<FitnessProfile & { _filterOn?: boolean }>) => {
    setFitnessProfile((prev) => {
      const next = { ...prev, ...updates };
      try {
        localStorage.setItem("trailblaze_fitness", JSON.stringify({ ...next, _filterOn: updates._filterOn ?? fitnessFilterOn }));
      } catch {}
      return next;
    });
    if (updates._filterOn !== undefined) {
      setFitnessFilterOn(updates._filterOn);
    }
  };

  // Isochrone state
  const [isoAddress, setIsoAddress] = useState("");
  const [isoDuration, setIsoDuration] = useState<number>(60);
  const [isoPolygon, setIsoPolygon] = useState<IsochroneResponse["polygon"] | null>(null);
  const [isoLoading, setIsoLoading] = useState(false);
  const [isoError, setIsoError] = useState<string | null>(null);
  const [isoApproximate, setIsoApproximate] = useState(false);
  const [isoMessage, setIsoMessage] = useState<string | null>(null);

  const REGION_BOUNDS: Record<string, [[number, number], [number, number]]> = {
    "Rocky Mountains":   [[40.1, -105.9], [40.7, -105.4]],
    "Boulder":           [[39.9, -105.4], [40.1, -105.0]],
    "Denver Foothills":  [[39.6, -105.3], [39.9, -104.9]],
    "Colorado Springs":  [[38.7, -105.0], [39.0, -104.6]],
    "Aspen":             [[39.0, -107.0], [39.3, -106.6]],
    "Telluride":         [[37.8, -108.0], [38.0, -107.6]],
    "Steamboat Springs": [[40.4, -107.0], [40.6, -106.6]],
  };

  // Load ALL trails on mount and when filter changes
  useEffect(() => {
    fetchFeaturedTrails(10000, filterDifficulty)
      .then((res) => setFeaturedTrails(res.trails))
      .catch(() => {});
  }, [filterDifficulty]);

  // Point-in-polygon ray casting (no npm package)
  function pointInPolygon(point: [number, number], polygon: number[][]): boolean {
    const [y, x] = point; // [lat, lng]
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i][0], yi = polygon[i][1];
      const xj = polygon[j][0], yj = polygon[j][1];
      const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }

  const handleIsochroneSearch = async () => {
    if (!isoAddress.trim()) return;
    setIsoLoading(true);
    setIsoError(null);
    try {
      // Geocode the address using Nominatim
      const geoRes = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(isoAddress)}&format=json&limit=1`,
        { headers: { "User-Agent": "TrailBlazeAI/1.0" } }
      );
      const geoData = await geoRes.json();
      if (!geoData.length) {
        setIsoError("Location not found. Try a more specific address.");
        setIsoLoading(false);
        return;
      }
      const lat = parseFloat(geoData[0].lat);
      const lng = parseFloat(geoData[0].lon);

      const result = await fetchIsochrone(lat, lng, isoDuration);
      if (result.error) {
        setIsoError(result.error);
        setIsoPolygon(null);
        setIsoApproximate(false);
        setIsoMessage(null);
      } else if (result.polygon) {
        setIsoPolygon(result.polygon);
        setIsoApproximate(result.approximate ?? false);
        setIsoMessage(result.message ?? null);
      }
    } catch (err) {
      setIsoError("Failed to calculate drive time area.");
    } finally {
      setIsoLoading(false);
    }
  };

  const clearIsochrone = () => {
    setIsoPolygon(null);
    setIsoAddress("");
    setIsoError(null);
    setIsoApproximate(false);
    setIsoMessage(null);
  };

  const toggleDarkMode = () => {
    setDarkMode((prev) => {
      const next = !prev;
      try { localStorage.setItem("trailblaze_dark", next ? "1" : "0"); } catch {}
      return next;
    });
  };

  const handleShare = (trail: MapTrail) => {
    const url = `${window.location.origin}${window.location.pathname}?trail=${encodeURIComponent(trail.name)}`;
    navigator.clipboard.writeText(url).then(() => {
      setShareToast(true);
      setTimeout(() => setShareToast(false), 2500);
    });
  };

  const addToCompare = (trail: MapTrail) => {
    setCompareTrails((prev) => {
      if (prev.find((t) => t.name === trail.name) || prev.length >= 5) return prev;
      return [...prev, trail];
    });
    setCompareOpen(true);
  };

  const removeFromCompare = (name: string) => {
    setCompareTrails((prev) => {
      const next = prev.filter((t) => t.name !== name);
      if (!next.length) setCompareOpen(false);
      return next;
    });
  };

  const handleSurpriseMe = async () => {
    setSurpriseLoading(true);
    try {
      const result = await fetchSurpriseTrail(filterDifficulty);
      if (result?.trail) {
        setHighlightedTrails([result.trail]);
        setWeatherContext(result.tagline);
        handleCardClick(result.trail);
      }
    } catch {}
    setSurpriseLoading(false);
  };

  const handleTrailsReferenced = (trails: TrailReference[], weather?: string) => {
    setHighlightedTrails(trails);
    setWeatherContext(weather);
    setSelectedTrail(null);
    setClusterTrails(null);
  };

  // When a trail card in the sidebar is clicked
  const handleCardClick = useCallback((trail: TrailReference) => {
    const mapTrail = featuredTrails.find(
      (ft) => ft.name.toLowerCase() === trail.name.toLowerCase()
    );
    if (mapTrail) {
      setSelectedTrail(mapTrail);
    } else {
      setSelectedTrail({
        name: trail.name,
        difficulty: trail.difficulty,
        length_miles: trail.length_miles,
        location: trail.location,
        nearby_city: trail.nearby_city,
        review_count: 0,
        trailblaze_score: trail.trailblaze_score,
      });
    }
  }, [featuredTrails]);

  // When a pin is clicked on the map
  const handleMapPinClick = useCallback((trail: MapTrail) => {
    setSelectedTrail(trail);
  }, []);

  // When a cluster is clicked on the map — show drawer for small, sidebar for large
  const handleClusterClick = useCallback((trails: MapTrail[]) => {
    if (trails.length <= 5) {
      setDrawerTrails(trails);
      setDrawerOpen(true);
    } else {
      setClusterTrails(trails);
      setSelectedTrail(null);
    }
  }, []);

  const handleRegionClick = async (region: string) => {
    if (activeRegion === region) {
      setActiveRegion(null);
      setMapBounds([[37.0, -109.1], [41.0, -102.0]]);
      fetchFeaturedTrails(10000, filterDifficulty)
        .then((res) => setFeaturedTrails(res.trails))
        .catch(() => {});
    } else {
      setActiveRegion(region);
      setMapBounds(REGION_BOUNDS[region]);
      try {
        const trails = await fetchTrailsByRegion(
          region,
          filterDifficulty || undefined,
          undefined,
          200
        );
        setFeaturedTrails(trails.map((t) => ({
          name: t.name,
          difficulty: t.difficulty,
          length_miles: t.length_miles,
          elevation_gain_ft: t.elevation_gain_ft,
          manager: t.manager,
          review_count: 0,
          trailblaze_score: t.trailblaze_score,
        })));
      } catch {
        // silently ignore fetch failures
      }
    }
    setClusterTrails(null);
  };

  // The trails to display in sidebar
  const filteredByIsochrone = isoPolygon && isoPolygon.coordinates
    ? featuredTrails.filter((t) => {
        if (!t.lat || !t.lng) return false;
        const ring = isoPolygon.coordinates[0];
        return pointInPolygon([t.lat, t.lng], ring);
      })
    : null;

  const baseTrails = filteredByIsochrone ?? featuredTrails;

  const favFiltered = showFavoritesOnly
    ? baseTrails.filter((t) => favorites.includes(t.name))
    : baseTrails;

  const sidebarTrails = clusterTrails
    ? clusterTrails
    : searchQuery
      ? favFiltered.filter((t) =>
          t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (t.nearby_city || "").toLowerCase().includes(searchQuery.toLowerCase())
        )
      : favFiltered;

  const sidebarTitle = clusterTrails
    ? `${clusterTrails.length} Trails in Area`
    : "All Trails";

  return (
    <div className={`h-screen flex relative overflow-hidden pb-14 md:pb-0 ${darkMode ? "dark bg-gray-950" : ""}`}>
      {/* Left Sidebar — Desktop: always visible, Mobile: shown as overlay on search/saved tab */}
      <div className={`
        ${mobileTab === "search" || mobileTab === "saved" ? "flex" : "hidden"} md:flex
        fixed inset-0 z-30 md:static md:z-10
        w-full md:w-[360px] h-full flex-col bg-white md:border-r border-gray-200 md:shrink-0
      `}>
        {/* Header */}
        <div className="px-4 py-3 bg-gradient-to-r from-emerald-800 to-emerald-700 flex items-center gap-3">
          {/* Mobile back button */}
          <button
            onClick={() => setMobileTab("map")}
            className="md:hidden p-1.5 rounded-lg bg-white/10 text-emerald-200 hover:bg-white/20 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
          <Mountain className="w-6 h-6 text-amber-400" />
          <div className="flex-1">
            <h1 className="text-lg font-bold text-white leading-tight">TrailBlaze AI</h1>
            <p className="text-[11px] text-emerald-200">Colorado Trail Explorer</p>
          </div>
          <button
            onClick={() => setFitnessOpen(!fitnessOpen)}
            className={`p-2 rounded-lg transition-colors ${fitnessOpen ? "bg-white/20 text-white" : "bg-white/10 text-emerald-200 hover:bg-white/20 hover:text-white"}`}
            title="Fitness Profile"
          >
            <Settings className="w-5 h-5" />
          </button>
          <button
            onClick={() => setItineraryOpen(true)}
            className="p-2 rounded-lg bg-white/10 text-emerald-200 hover:bg-white/20 hover:text-white transition-colors"
            title="Plan My Hike"
          >
            <CalendarDays className="w-5 h-5" />
          </button>
          <button
            onClick={toggleDarkMode}
            className="p-2 rounded-lg bg-white/10 text-emerald-200 hover:bg-white/20 hover:text-white transition-colors"
            title={darkMode ? "Light mode" : "Dark mode"}
          >
            {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
          <button
            onClick={() => chatOpen ? setChatOpen(false) : handleOpenChat()}
            className={`hidden md:block p-2 rounded-lg transition-colors ${chatOpen ? "bg-white/20 text-white" : "bg-white/10 text-emerald-200 hover:bg-white/20 hover:text-white"}`}
            title="AI Assistant"
          >
            <MessageSquare className="w-5 h-5" />
          </button>
        </div>

        {/* Saved Trails chip + Browse by Region */}
        <div className="px-3 pt-2.5 pb-1 border-b border-gray-100">
          <div className="flex items-center gap-2 mb-1.5">
            <button
              onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border cursor-pointer ${
                showFavoritesOnly
                  ? "bg-red-50 border-red-300 text-red-600"
                  : "bg-transparent border-gray-300 text-gray-500 hover:border-red-400 hover:text-red-500"
              }`}
            >
              <Heart className={`w-3 h-3 ${showFavoritesOnly ? "fill-red-500 text-red-500" : ""}`} />
              Saved ({favorites.length})
            </button>
            <p className="text-[10px] text-gray-400 uppercase tracking-wider">Browse by Region</p>
          </div>
          <div className="flex flex-wrap gap-1.5 pb-1.5">
            {Object.keys(REGION_BOUNDS).map((region) => (
              <button
                key={region}
                onClick={() => handleRegionClick(region)}
                className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border cursor-pointer ${
                  activeRegion === region
                    ? "bg-emerald-700 border-emerald-700 text-white"
                    : "bg-transparent border-gray-300 text-gray-500 hover:border-emerald-600 hover:text-emerald-700"
                }`}
              >
                {region}
              </button>
            ))}
          </div>
        </div>

        {/* Conditions Feed toggle */}
        <div className="px-3 py-1.5 border-b border-gray-100">
          <button
            onClick={() => setConditionsOpen((o) => !o)}
            className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              conditionsOpen ? "bg-emerald-50 text-emerald-700" : "text-gray-500 hover:bg-gray-50"
            }`}
          >
            <span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5" /> Live Trail Conditions</span>
            <span className="text-gray-300">{conditionsOpen ? "▲" : "▼"}</span>
          </button>
          {conditionsOpen && (
            <ConditionsFeed
              onTrailClick={(name) => handleCardClick({ name })}
            />
          )}
        </div>

        {/* Surprise Me */}
        <div className="px-3 py-2 border-b border-gray-100">
          <button
            onClick={handleSurpriseMe}
            disabled={surpriseLoading}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gradient-to-r from-purple-500 to-indigo-500 text-white text-xs font-semibold rounded-lg hover:from-purple-600 hover:to-indigo-600 disabled:opacity-50 transition-all cursor-pointer"
          >
            {surpriseLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <span>🎲</span>}
            {surpriseLoading ? "Finding a gem..." : "Surprise Me!"}
          </button>
        </div>

        {/* Isochrone / Drive-Time Filter */}
        <div className="px-3 py-2.5 border-b border-gray-100 space-y-2">
          <div className="flex items-center gap-1.5">
            <Car className="w-3.5 h-3.5 text-blue-600" />
            <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Within drive time</p>
          </div>
          <div className="flex gap-1">
            {[{ label: "30 min", value: 30 }, { label: "1 hr", value: 60 }, { label: "1.5 hr", value: 90 }, { label: "2 hr", value: 120 }].map((opt) => (
              <button
                key={opt.value}
                onClick={() => setIsoDuration(opt.value)}
                className={`flex-1 px-1.5 py-1 rounded-md text-[10px] font-medium transition-colors border cursor-pointer ${
                  isoDuration === opt.value
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-gray-50 text-gray-500 border-gray-200 hover:border-blue-400"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <input
            type="text"
            placeholder="e.g. Denver, CO"
            value={isoAddress}
            onChange={(e) => setIsoAddress(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleIsochroneSearch(); }}
            className="w-full px-3 py-1.5 rounded-lg border border-gray-200 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50"
          />
          {isoError && <p className="text-[10px] text-red-500">{isoError}</p>}
          <div className="flex gap-1.5">
            <button
              onClick={handleIsochroneSearch}
              disabled={isoLoading || !isoAddress.trim()}
              className="flex-1 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-1.5"
            >
              {isoLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Car className="w-3 h-3" />}
              {isoLoading ? "Calculating..." : "Show trails"}
            </button>
            {isoPolygon && (
              <button
                onClick={clearIsochrone}
                className="px-3 py-1.5 bg-gray-100 text-gray-600 text-xs font-medium rounded-lg hover:bg-gray-200 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
          {isoPolygon && (
            <div className="space-y-1">
              <p className="text-[10px] text-blue-600 font-medium">
                Showing {filteredByIsochrone?.length ?? 0} trails within {isoDuration} min drive
              </p>
              {isoApproximate && (
                <div className="flex items-start gap-1.5 rounded-md bg-amber-50 border border-amber-200 px-2 py-1.5">
                  <span className="text-amber-500 text-xs leading-none mt-0.5">⚠</span>
                  <p className="text-[10px] text-amber-700 leading-tight">
                    {isoMessage || "Using distance approximation. Set ORS_API_KEY for accurate drive-time polygons."}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Search + Filters */}
        <div className="px-3 py-2.5 border-b border-gray-100 space-y-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search trails..."
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setClusterTrails(null); }}
              className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent bg-gray-50"
            />
          </div>
          <div className="flex gap-1.5">
            {[
              { label: "All", value: undefined },
              { label: "Easy", value: "easy" },
              { label: "Moderate", value: "moderate" },
              { label: "Hard", value: "hard" },
            ].map((f) => (
              <button
                key={f.label}
                onClick={() => { setFilterDifficulty(f.value); setClusterTrails(null); }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  filterDifficulty === f.value
                    ? "bg-emerald-700 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Cluster indicator + trail count */}
        <div className="px-4 py-2 text-[11px] font-medium text-gray-400 uppercase tracking-wider bg-gray-50/50 flex items-center justify-between">
          <span>{sidebarTrails.length} trails {clusterTrails ? "in cluster" : "found"}</span>
          {clusterTrails && (
            <button
              onClick={() => setClusterTrails(null)}
              className="text-emerald-600 hover:text-emerald-700 font-semibold normal-case text-[11px]"
            >
              Show all
            </button>
          )}
        </div>

        {/* Trail List */}
        <div className="flex-1 overflow-y-auto">
          {highlightedTrails.length > 0 && !clusterTrails && (
            <div className="border-b-2 border-emerald-100">
              <TrailCards
                trails={highlightedTrails}
                weatherContext={weatherContext}
                title="AI Recommendations"
                onTrailClick={handleCardClick}
              />
            </div>
          )}
          <TrailCards
            trails={sidebarTrails.map((t) => ({
              name: t.name,
              difficulty: t.difficulty,
              length_miles: t.length_miles,
              elevation_gain_ft: t.elevation_gain_ft,
              surface: t.surface,
              location: t.location,
              nearby_city: t.nearby_city,
              trailblaze_score: t.trailblaze_score,
            }))}
            title={sidebarTitle}
            onTrailClick={handleCardClick}
            fitnessProfile={fitnessFilterOn ? fitnessProfile : undefined}
            favorites={favorites}
            onToggleFavorite={toggleFavorite}
          />
        </div>
      </div>

      {/* Map — takes remaining space */}
      <div className="flex-1 h-full relative">
        <TrailMap
          featuredTrails={featuredTrails}
          selectedTrail={selectedTrail}
          highlightedTrails={highlightedTrails}
          onTrailClick={handleMapPinClick}
          onClusterClick={handleClusterClick}
          mapBounds={mapBounds}
          isochronePolygon={isoPolygon}
        />
      </div>

      {/* Trail Detail Panel — slides in from right when a trail is selected */}
      {selectedTrail && (
        <TrailDetail
          trail={selectedTrail}
          onClose={() => setSelectedTrail(null)}
          onTrailClick={(t) => setSelectedTrail(t)}
          isFavorite={favorites.includes(selectedTrail.name)}
          onToggleFavorite={() => toggleFavorite(selectedTrail.name)}
          onShare={() => handleShare(selectedTrail)}
          onCompare={() => addToCompare(selectedTrail)}
          isComparing={compareTrails.some((t) => t.name === selectedTrail.name)}
        />
      )}

      {/* Share toast */}
      {shareToast && (
        <div className="fixed bottom-20 md:bottom-6 left-1/2 -translate-x-1/2 z-[10000] bg-gray-900 text-white text-xs px-4 py-2 rounded-full shadow-lg flex items-center gap-2 animate-fade-in">
          <Share2 className="w-3.5 h-3.5" /> Link copied to clipboard!
        </div>
      )}

      {/* Trail Comparison bar */}
      {compareOpen && compareTrails.length > 0 && (
        <TrailComparison
          trails={compareTrails}
          onRemove={removeFromCompare}
          onClose={() => setCompareOpen(false)}
        />
      )}

      {/* Floating Chat Panel — full-screen on mobile, floating card on desktop */}
      {(chatOpen || mobileTab === "chat") && (
        <div
          className={`fixed inset-0 md:inset-auto md:bottom-4 md:right-4 md:w-[380px] md:h-[540px] bg-white md:rounded-2xl shadow-2xl flex flex-col overflow-hidden md:border border-gray-200 z-[9999] pb-14 md:pb-0 ${selectedTrail ? "md:right-[356px]" : ""}`}
        >
          <div className="flex items-center justify-between px-3 py-2.5 bg-gradient-to-r from-emerald-700 to-emerald-600 shrink-0">
            <span className="text-sm font-semibold text-white flex items-center gap-2">
              <MessageSquare className="w-4 h-4" /> AI Trail Assistant
            </span>
            <button onClick={() => { setChatOpen(false); setMobileTab("map"); }} className="p-1 rounded hover:bg-white/20 text-white transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel
              onTrailsReferenced={handleTrailsReferenced}
              sessionId={sessionId}
              onSessionCreated={setSessionId}
            />
          </div>
        </div>
      )}
      {/* Fitness Profile Settings Panel */}
      {fitnessOpen && (
        <div className="fixed inset-0 z-[9998]" onClick={() => setFitnessOpen(false)}>
          <div
            className="absolute inset-0 md:inset-auto md:top-0 md:left-[360px] md:w-[300px] md:h-full bg-white shadow-2xl md:border-r border-gray-200 overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 py-3 bg-gradient-to-r from-emerald-700 to-emerald-600 flex items-center justify-between">
              <span className="text-sm font-semibold text-white flex items-center gap-2">
                <Settings className="w-4 h-4" /> My Fitness Profile
              </span>
              <button onClick={() => setFitnessOpen(false)} className="p-1 rounded hover:bg-white/20 text-white transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 space-y-5">
              {/* Filter toggle */}
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Filter trails to my level</span>
                <button
                  onClick={() => updateFitness({ _filterOn: !fitnessFilterOn })}
                  className={`relative w-11 h-6 rounded-full transition-colors ${
                    fitnessFilterOn ? "bg-emerald-600" : "bg-gray-300"
                  }`}
                >
                  <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    fitnessFilterOn ? "translate-x-5" : ""
                  }`} />
                </button>
              </div>

              {/* Fitness level */}
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Fitness Level</label>
                <div className="flex gap-2 mt-1.5">
                  {(["beginner", "intermediate", "advanced"] as const).map((level) => (
                    <button
                      key={level}
                      onClick={() => updateFitness({ fitness_level: level })}
                      className={`flex-1 py-1.5 text-xs font-medium rounded-lg border transition-colors capitalize ${
                        fitnessProfile.fitness_level === level
                          ? "bg-emerald-600 text-white border-emerald-600"
                          : "bg-gray-50 text-gray-600 border-gray-200 hover:border-emerald-400"
                      }`}
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </div>

              {/* Max distance */}
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Max Distance: {fitnessProfile.max_distance_miles} mi
                </label>
                <input
                  type="range"
                  min={1}
                  max={30}
                  step={1}
                  value={fitnessProfile.max_distance_miles}
                  onChange={(e) => updateFitness({ max_distance_miles: Number(e.target.value) })}
                  className="w-full mt-1.5 accent-emerald-600"
                />
                <div className="flex justify-between text-[10px] text-gray-400">
                  <span>1 mi</span><span>30 mi</span>
                </div>
              </div>

              {/* Max elevation gain */}
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Max Elevation Gain: {fitnessProfile.max_elevation_gain_ft.toLocaleString()} ft
                </label>
                <input
                  type="range"
                  min={0}
                  max={5000}
                  step={100}
                  value={fitnessProfile.max_elevation_gain_ft}
                  onChange={(e) => updateFitness({ max_elevation_gain_ft: Number(e.target.value) })}
                  className="w-full mt-1.5 accent-emerald-600"
                />
                <div className="flex justify-between text-[10px] text-gray-400">
                  <span>0 ft</span><span>5,000 ft</span>
                </div>
              </div>

              {/* Surface preference */}
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Surface Preference</label>
                <select
                  value={fitnessProfile.preferred_surface}
                  onChange={(e) => updateFitness({ preferred_surface: e.target.value as FitnessProfile["preferred_surface"] })}
                  className="w-full mt-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="any">Any</option>
                  <option value="paved">Paved</option>
                  <option value="dirt">Dirt</option>
                  <option value="gravel">Gravel</option>
                </select>
              </div>

              <p className="text-[10px] text-gray-400 text-center">
                Settings saved automatically
              </p>
            </div>
          </div>
        </div>
      )}
      {/* Itinerary Builder modal */}
      {itineraryOpen && (
        <ItineraryBuilder
          onClose={() => setItineraryOpen(false)}
          defaultRegion={activeRegion || undefined}
        />
      )}

      {/* Cluster Drawer for small clusters */}
      <ClusterDrawer
        trails={drawerTrails}
        isOpen={drawerOpen}
        onTrailSelect={(trail) => {
          setSelectedTrail(trail);
          setDrawerOpen(false);
        }}
        onClose={() => setDrawerOpen(false)}
      />

      {/* Floating Chat FAB — desktop only (mobile uses bottom nav) */}
      {!chatOpen && (
        <button
          onClick={handleOpenChat}
          className={`hidden md:flex fixed bottom-6 right-6 z-[9999] bg-green-600 hover:bg-green-700 text-white rounded-full w-16 h-16 items-center justify-center shadow-2xl transition-all duration-200 hover:scale-110 ${!chatSeen ? "animate-pulse" : ""}`}
          aria-label="Open AI Chat"
        >
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </button>
      )}

      {/* Mobile Bottom Navigation Bar */}
      <nav className="fixed bottom-0 left-0 right-0 z-[9998] md:hidden bg-white border-t border-gray-200 flex items-center justify-around h-14 safe-area-bottom">
        {([
          { tab: "map" as const, icon: <Map className="w-5 h-5" />, label: "Map" },
          { tab: "search" as const, icon: <Search className="w-5 h-5" />, label: "Search" },
          { tab: "chat" as const, icon: <MessageSquare className="w-5 h-5" />, label: "Chat" },
          { tab: "saved" as const, icon: <Heart className="w-5 h-5" />, label: "Saved" },
        ]).map((item) => (
          <button
            key={item.tab}
            onClick={() => {
              setMobileTab(item.tab);
              if (item.tab === "chat") { setChatOpen(true); setChatSeen(true); localStorage.setItem("chat_seen", "1"); }
              if (item.tab === "saved") setShowFavoritesOnly(true);
              if (item.tab === "search") setShowFavoritesOnly(false);
              if (item.tab === "map") { setChatOpen(false); }
            }}
            className={`flex flex-col items-center justify-center flex-1 py-1 transition-colors ${
              mobileTab === item.tab
                ? "text-emerald-700"
                : "text-gray-400 hover:text-gray-600"
            }`}
          >
            {item.icon}
            <span className="text-[10px] font-medium mt-0.5">{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
