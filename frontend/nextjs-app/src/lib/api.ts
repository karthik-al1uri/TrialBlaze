/**
 * API client for the TrailBlaze backend.
 * Uses Next.js rewrites to proxy /api/* to the backend.
 */

export interface TrailReference {
  name: string;
  difficulty?: string;
  length_miles?: number;
  elevation_gain_ft?: number;
  surface?: string;
  location?: string;
  nearby_city?: string;
  trailblaze_score?: number;
  wildlife_alert?: boolean;
  wildlife_alert_species?: string[];
}

export interface ChatResponse {
  answer: string;
  route?: string;
  trails_referenced: TrailReference[];
  weather_context?: string;
  session_id?: string;
  quality_check?: Record<string, unknown>;
}

export interface Trail {
  cotrex_fid?: number;
  name: string;
  trail_type?: string;
  surface?: string;
  difficulty?: string;
  length_miles?: number;
  min_elevation_ft?: number;
  max_elevation_ft?: number;
  elevation_gain_ft?: number;
  hiking?: boolean;
  bike?: boolean;
  horse?: boolean;
  dogs?: string;
  manager?: string;
  reviews?: { text: string; rating: number; source: string }[];
  trailblaze_score?: number;
  wildlife_alert?: boolean;
  wildlife_alert_species?: string[];
}

export interface TrailListResponse {
  trails: Trail[];
  total: number;
  page: number;
  page_size: number;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000';

const BASE = "";

export async function sendChat(
  query: string,
  sessionId?: string,
  language: string = "en"
): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId, language }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}

export async function fetchTrails(
  page = 1,
  pageSize = 20,
  filters: Record<string, string> = {}
): Promise<TrailListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    ...filters,
  });
  const res = await fetch(`${BASE}/api/trails?${params}`);
  if (!res.ok) throw new Error(`Trails fetch failed: ${res.status}`);
  return res.json();
}

export async function searchTrails(
  name: string,
  pageSize = 10
): Promise<TrailListResponse> {
  const res = await fetch(
    `${BASE}/api/trails/search/${encodeURIComponent(name)}?page_size=${pageSize}`
  );
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json();
}

export interface BestDayPrediction {
  trail_name: string;
  best_date: string;
  score: number;
  reason: string;
  daily_scores: { date: string; score: number }[];
}

export async function fetchBestDayPrediction(
  trailName: string
): Promise<BestDayPrediction | null> {
  try {
    const res = await fetch(
      `${BASE}/api/trails/best-day/${encodeURIComponent(trailName)}`
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export interface CrowdForecastDay {
  date: string;
  score: number;
  level: string;
}

export interface CrowdPrediction {
  trail_name: string;
  target_date: string;
  score: number;
  level: string;
  best_time: string;
  weekly_forecast: CrowdForecastDay[];
}

export async function fetchCrowdPrediction(
  trailName: string,
  date?: string
): Promise<CrowdPrediction | null> {
  try {
    const params = new URLSearchParams();
    if (date) params.set("date", date);
    const q = params.toString();
    const res = await fetch(
      `${BASE}/api/trails/crowd/${encodeURIComponent(trailName)}${q ? `?${q}` : ""}`
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export interface SeasonalHeatmap {
  trail_name: string;
  best_months: number[];
  worst_months: number[];
  monthly_scores: Record<string, number>;
}

export async function fetchSeasonalHeatmap(
  trailName: string
): Promise<SeasonalHeatmap | null> {
  try {
    const res = await fetch(
      `${BASE}/api/trails/seasonal/${encodeURIComponent(trailName)}`
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export interface IsochroneResponse {
  polygon: {
    type: string;
    coordinates: number[][][];
  } | null;
  duration_minutes: number;
  center: { lat: number; lng: number };
  error?: string;
  approximate?: boolean;
  message?: string;
}

export async function fetchIsochrone(
  lat: number,
  lng: number,
  durationMinutes: number = 60
): Promise<IsochroneResponse> {
  const params = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
    duration_minutes: String(durationMinutes),
  });
  const res = await fetch(`${BASE}/api/isochrone?${params}`);
  if (!res.ok) throw new Error(`Isochrone fetch failed: ${res.status}`);
  return res.json();
}

export interface MapTrail {
  name: string;
  difficulty?: string;
  length_miles?: number;
  elevation_gain_ft?: number;
  manager?: string;
  location?: string;
  nearby_city?: string;
  lat?: number;
  lng?: number;
  hiking?: boolean;
  dogs?: string;
  surface?: string;
  avg_rating?: number;
  review_count: number;
  hp_rating?: number;
  hp_summary?: string;
  hp_condition?: string;
  trailblaze_score?: number;
  wildlife_alert?: boolean;
  wildlife_alert_species?: string[];
}

export interface MapTrailsResponse {
  trails: MapTrail[];
  total: number;
}

export async function fetchFeaturedTrails(
  limit = 30,
  difficulty?: string
): Promise<MapTrailsResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (difficulty) params.set("difficulty", difficulty);
  const res = await fetch(`${BASE}/api/trails/featured?${params}`);
  if (!res.ok) throw new Error(`Featured trails fetch failed: ${res.status}`);
  return res.json();
}

export interface ElevationPoint {
  distance_mi: number;
  elev_ft: number;
}

export interface TrailGeometry {
  name: string;
  feature_id?: number;
  coordinates: [number, number][]; // [lng, lat][]
  elevation_profile?: ElevationPoint[];
}

export interface TrailheadPoint {
  name: string;
  latitude: number;
  longitude: number;
}

export interface GeometryResponse {
  trails: TrailGeometry[];
  trailheads: TrailheadPoint[];
}

export async function fetchGeometry(
  trailNames: string[]
): Promise<GeometryResponse> {
  const names = trailNames.join(",");
  const res = await fetch(
    `${BASE}/api/geometry?names=${encodeURIComponent(names)}`
  );
  if (!res.ok) throw new Error(`Geometry fetch failed: ${res.status}`);
  return res.json();
}

export interface TrailPhoto {
  title: string;
  url: string;
  thumb_url: string;
  description: string;
}

export interface PhotoResponse {
  trail_name: string;
  photos: TrailPhoto[];
}

export async function fetchPhotos(
  name: string,
  location?: string
): Promise<PhotoResponse> {
  const params = new URLSearchParams({ name });
  if (location) params.set("location", location);
  const res = await fetch(`${BASE}/api/photos?${params}`);
  if (!res.ok) throw new Error(`Photos fetch failed: ${res.status}`);
  return res.json();
}

// --- Weather ---

export interface DayForecast {
  date: string;
  weather_code: number;
  weather_desc: string;
  weather_icon: string;
  temp_high_f: number;
  temp_low_f: number;
  precipitation_sum_in: number;
  snowfall_sum_in: number;
  wind_max_mph: number;
  precipitation_prob: number;
}

export interface CurrentWeather {
  temp_f: number;
  feels_like_f: number;
  humidity_pct: number;
  weather_code: number;
  weather_desc: string;
  weather_icon: string;
  wind_mph: number;
  wind_gusts_mph: number;
  uv_index: number;
}

export interface WeatherResponse {
  location: string;
  lat: number;
  lng: number;
  current?: CurrentWeather;
  forecast: DayForecast[];
  safety_notes: string[];
  hiking_advisory: string;
  error?: string;
}

export async function fetchWeather(
  lat: number,
  lng: number,
  location: string = "Trail area"
): Promise<WeatherResponse> {
  const params = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
    location,
  });
  const res = await fetch(`${BASE}/api/weather?${params}`);
  if (!res.ok) throw new Error(`Weather fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchTrailsByRegion(
  region: string,
  difficulty?: string,
  source?: string,
  limit: number = 50
): Promise<Trail[]> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (difficulty) params.set("difficulty", difficulty);
  if (source) params.set("source", source);
  const res = await fetch(
    `${BASE}/api/trails/by-region/${encodeURIComponent(region)}?${params}`
  );
  if (!res.ok) throw new Error("Failed to fetch trails by region");
  return res.json();
}

export interface ConditionReport {
  id: string;
  trail_name: string;
  condition: string;
  note: string;
  reported_at: string;
}

export async function fetchTrailConditions(
  trailName: string
): Promise<ConditionReport[]> {
  try {
    const res = await fetch(
      `${BASE}/api/conditions/${encodeURIComponent(trailName)}`
    );
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function submitTrailCondition(
  trailName: string,
  condition: string,
  note?: string
): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/api/conditions/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        trail_name: trailName,
        condition,
        note: note || "",
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export interface WildlifeObservation {
  name: string;
  scientific: string;
  observed_on: string;
  photo_url: string | null;
  iconic_taxon: string;
}

export async function fetchWildlifeNearTrail(
  lat: number,
  lng: number,
  radiusMiles: number = 2
): Promise<WildlifeObservation[]> {
  try {
    const params = new URLSearchParams({
      lat: String(lat),
      lng: String(lng),
      radius: String(radiusMiles),
      quality_grade: "research",
      per_page: "12",
      order_by: "observed_on",
      order: "desc",
    });
    const res = await fetch(
      `https://api.inaturalist.org/v1/observations?${params}`,
      { signal: AbortSignal.timeout(8000) }
    );
    if (!res.ok) return [];
    const data = await res.json();
    const seen = new Set<string>();
    const results: WildlifeObservation[] = [];
    for (const obs of data.results) {
      if (!obs.taxon) continue;
      const name = obs.taxon.preferred_common_name || obs.taxon.name;
      if (!name || seen.has(name)) continue;
      seen.add(name);
      results.push({
        name,
        scientific: obs.taxon.name || "",
        observed_on: obs.observed_on || "",
        photo_url: obs.taxon.default_photo?.square_url || null,
        iconic_taxon: obs.taxon.iconic_taxon_name || "Unknown",
      });
      if (results.length >= 6) break;
    }
    return results;
  } catch {
    return [];
  }
}

// --- Reviews ---

export interface Review {
  id: string;
  trail_name: string;
  rating: number;
  title: string;
  body: string;
  hike_date: string;
  difficulty_felt: string;
  reported_at: string;
}

export interface ReviewSummary {
  average_rating: number;
  total_reviews: number;
  rating_breakdown: Record<number, number>;
  difficulty_breakdown: {
    easier: number;
    as_expected: number;
    harder: number;
  };
  sentiment_summary?: {
    positive_pct: number;
    themes: Record<string, number>;
    last_analyzed: string;
    review_count_analyzed: number;
  } | null;
}

export async function fetchReviews(
  trailName: string,
  limit: number = 10
): Promise<Review[]> {
  try {
    const params = new URLSearchParams({
      limit: String(limit),
      sort: "newest",
    });
    const res = await fetch(
      `${BASE}/api/reviews/${encodeURIComponent(trailName)}?${params}`
    );
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function fetchReviewSummary(
  trailName: string
): Promise<ReviewSummary | null> {
  try {
    const res = await fetch(
      `${BASE}/api/reviews/${encodeURIComponent(trailName)}/summary`
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function submitReview(review: {
  trail_name: string;
  rating: number;
  title?: string;
  body?: string;
  hike_date?: string;
  difficulty_felt?: string;
}): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/api/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(review),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export interface SunTimesResponse {
  sunrise?: string | null;
  sunset?: string | null;
  solar_noon?: string | null;
  day_length?: string | null;
  golden_hour_start?: string | null;
  error?: string | null;
}

export async function fetchSunTimes(
  lat: number,
  lng: number
): Promise<SunTimesResponse> {
  try {
    const res = await fetch(`${BASE}/api/sun?lat=${lat}&lng=${lng}`);
    if (!res.ok) return { error: "Failed to fetch" };
    return res.json();
  } catch {
    return { error: "Network error" };
  }
}

export async function generateItinerary(
  days: number = 3,
  difficulty?: string,
  region?: string,
  interests?: string
): Promise<{ itinerary: string; days: number }> {
  try {
    const res = await fetch(`${BASE}/api/itineraries/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ days, difficulty, region, interests }),
    });
    if (!res.ok) return { itinerary: "Failed to generate itinerary.", days };
    return res.json();
  } catch {
    return { itinerary: "Network error generating itinerary.", days };
  }
}

export interface SurpriseTrailResponse {
  trail: TrailReference;
  tagline: string;
}

export async function fetchSurpriseTrail(
  difficulty?: string
): Promise<SurpriseTrailResponse | null> {
  try {
    const params = new URLSearchParams();
    if (difficulty) params.set("difficulty", difficulty);
    const q = params.toString();
    const res = await fetch(`${BASE}/api/trails/surprise${q ? `?${q}` : ""}`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export interface NPSAlert {
  title: string;
  description: string;
  category: string;
  url?: string | null;
}

export interface NPSAlertsResponse {
  alerts: NPSAlert[];
  park_code: string;
  error?: string | null;
}

export async function fetchNPSAlerts(
  parkCode: string = "romo"
): Promise<NPSAlertsResponse> {
  try {
    const res = await fetch(`${BASE}/api/nps/alerts?park_code=${encodeURIComponent(parkCode)}`);
    if (!res.ok) return { alerts: [], park_code: parkCode, error: "Failed to fetch" };
    return res.json();
  } catch {
    return { alerts: [], park_code: parkCode, error: "Network error" };
  }
}

export async function fetchNarrative(
  trailName: string,
  weatherSummary: string = "",
  season: string = ""
): Promise<{ narrative: string }> {
  try {
    const res = await fetch(`${BASE}/api/trails/narrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        trail_name: trailName,
        weather_summary: weatherSummary,
        season: season,
      }),
    });
    if (!res.ok) return { narrative: "" };
    return res.json();
  } catch {
    return { narrative: "" };
  }
}

export async function fetchNearbyTrails(
  lat: number,
  lng: number,
  radiusMiles: number = 5,
  excludeName?: string,
  limit: number = 5
): Promise<Trail[]> {
  try {
    const params = new URLSearchParams({
      lat: String(lat),
      lng: String(lng),
      radius_miles: String(radiusMiles),
      limit: String(limit),
    });
    if (excludeName) params.set("exclude_name", excludeName);
    const res = await fetch(`${BASE}/api/trails/nearby?${params}`);
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

// --- GPX Data (inline viewer) ---

export interface GpxStats {
  distance_mi: number;
  elevation_gain_ft: number;
  elevation_loss_ft: number;
  min_elevation_ft: number | null;
  max_elevation_ft: number | null;
  waypoint_count: number;
}

export interface GpxElevationPoint {
  distance_mi: number;
  elev_ft: number;
}

export interface GpxDataResponse {
  gpx: string;
  stats: GpxStats;
  elevation_profile: GpxElevationPoint[];
}

export interface SimilarTrail {
  name: string;
  difficulty?: string;
  length_miles?: number;
  elevation_gain_ft?: number;
  nearby_city?: string;
  location?: string;
  trailblaze_score?: number;
  surface?: string;
}

export async function fetchSimilarTrails(
  trailName: string,
  limit = 5
): Promise<SimilarTrail[]> {
  try {
    const res = await fetch(
      `${BASE}/api/trails/similar/${encodeURIComponent(trailName)}?limit=${limit}`
    );
    if (!res.ok) return [];
    const data = await res.json();
    return data.similar_trails || [];
  } catch {
    return [];
  }
}

export interface RecentCondition {
  trail_name: string;
  condition: string;
  note: string;
  reported_at: string;
}

export async function fetchRecentConditions(
  limit = 15
): Promise<RecentCondition[]> {
  try {
    const res = await fetch(`${BASE}/api/conditions/recent?limit=${limit}`);
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function fetchGpxData(
  trailName: string
): Promise<GpxDataResponse | null> {
  try {
    const params = new URLSearchParams({ names: trailName });
    const res = await fetch(`${BASE}/api/geometry/gpx-data?${params}`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
