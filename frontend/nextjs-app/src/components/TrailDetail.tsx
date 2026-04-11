"use client";

import { useEffect, useState } from "react";
import {
  X,
  Mountain,
  MapPin,
  Ruler,
  TrendingUp,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  Dog,
  Footprints,
  Thermometer,
  Wind,
  Droplets,
  CloudSnow,
  AlertTriangle,
  Sun,
  Heart,
} from "lucide-react";
import {
  fetchPhotos,
  fetchWeather,
  fetchGeometry,
  fetchNearbyTrails,
  fetchBestDayPrediction,
  fetchCrowdPrediction,
  fetchSeasonalHeatmap,
  fetchTrailConditions,
  submitTrailCondition,
  fetchWildlifeNearTrail,
  fetchReviews,
  fetchReviewSummary,
  submitReview,
  fetchNarrative,
  fetchNPSAlerts,
  fetchSunTimes,
  type NPSAlert,
  type SunTimesResponse,
  type MapTrail,
  type Trail,
  type TrailPhoto,
  type WeatherResponse,
  type ConditionReport,
  type WildlifeObservation,
  type Review,
  type ReviewSummary,
  type BestDayPrediction,
  type CrowdPrediction,
  type SeasonalHeatmap,
} from "@/lib/api";
import ElevationProfile from "@/components/ElevationProfile";

/** Naismith's rule: 5 km/h + 1 hr per 600m ascent */
function estimateHikingTime(miles?: number, elevGainFt?: number): string {
  if (!miles) return "—";
  const km = miles * 1.60934;
  const gainM = (elevGainFt || 0) * 0.3048;
  const hours = km / 5 + gainM / 600;
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (m === 0) return `${h} hr`;
  return `${h} hr ${m} min`;
}

function getDiffStyle(d?: string) {
  switch (d) {
    case "easy":
      return { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500", label: "Easy" };
    case "moderate":
      return { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", label: "Moderate" };
    case "hard":
      return { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", label: "Hard" };
    default:
      return { bg: "bg-gray-50", text: "text-gray-600", dot: "bg-gray-400", label: "Unknown" };
  }
}

function adjustDifficulty(
  baseDifficulty: string | undefined,
  weather: { current?: { snow_depth_cm?: number; temperature_f?: number; wind_mph: number; precipitation?: number; temp_f: number } } | null
): { adjusted: string; reason: string } | null {
  if (!weather?.current || !baseDifficulty) return null;
  const cur = weather.current;
  const modifiers: string[] = [];
  let bump = 0;

  const snowDepth = (cur as any).snow_depth_cm ?? 0;
  const precip = (cur as any).precipitation ?? 0;
  const tempF = cur.temp_f;

  if (snowDepth > 8) { bump += 2; modifiers.push("deep snow"); }
  else if (snowDepth > 2) { bump += 1; modifiers.push("snow"); }
  if (tempF < 20) { bump += 1; modifiers.push("extreme cold"); }
  if (cur.wind_mph > 35) { bump += 1; modifiers.push("high winds"); }
  if (precip > 0.3) { bump += 1; modifiers.push("heavy rain"); }

  if (bump === 0) return null;

  const levels = ["easy", "moderate", "hard", "extreme"];
  const baseIdx = levels.indexOf(baseDifficulty.toLowerCase());
  const idx = baseIdx >= 0 ? baseIdx : 1;
  const newIdx = Math.min(levels.length - 1, idx + bump);
  const label = levels[newIdx].charAt(0).toUpperCase() + levels[newIdx].slice(1);

  return { adjusted: `${label} Today`, reason: modifiers.join(", ") };
}

function weatherSafetyScore(current: { temp_f: number; wind_mph: number; snow_depth_cm?: number; precipitation?: number }): {
  score: number; label: string; color: string;
} {
  let score = 100;
  const t = current.temp_f;
  const wind = current.wind_mph;
  const snow = ((current as any).snow_depth_cm ?? 0) / 2.54;
  const rain = (current as any).precipitation ?? 0;

  if (t < 20) score -= 30;
  else if (t < 32) score -= 15;
  else if (t > 95) score -= 20;

  if (wind > 40) score -= 25;
  else if (wind > 25) score -= 10;

  if (snow > 6) score -= 30;
  else if (snow > 2) score -= 15;

  if (rain > 0.5) score -= 20;
  else if (rain > 0.1) score -= 5;

  score = Math.max(0, Math.min(100, score));

  return {
    score,
    label: score >= 80 ? "Good" : score >= 50 ? "Fair" : score >= 20 ? "Poor" : "Dangerous",
    color: score >= 80 ? "text-green-400" : score >= 50 ? "text-amber-400" : score >= 20 ? "text-orange-400" : "text-red-500",
  };
}

function formatDay(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00");
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  const diff = Math.round((d.getTime() - today.getTime()) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function getSentimentThemeDisplay(theme: string, count: number): string {
  if (theme.toLowerCase().includes("view")) {
    return `👁 ${count} mention great views`;
  }
  if (theme.toLowerCase().includes("dog")) {
    return `🐾 ${count} mention dogs welcome`;
  }
  if (theme.toLowerCase().includes("parking")) {
    return `⚠️ ${count} mention crowded parking`;
  }
  if (theme.toLowerCase().includes("wildlife")) {
    return `🦌 ${count} mention wildlife`;
  }
  if (theme.toLowerCase().includes("steep")) {
    return `🥾 ${count} mention steep sections`;
  }
  if (theme.toLowerCase().includes("condition")) {
    return `🌦️ ${count} mention trail conditions`;
  }
  return `💬 ${count} mention ${theme}`;
}

function monthLabel(month: number): string {
  const labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return labels[Math.max(1, Math.min(12, month)) - 1];
}

interface TrailDetailProps {
  trail: MapTrail;
  onClose: () => void;
  onTrailClick?: (trail: MapTrail) => void;
  isFavorite?: boolean;
  onToggleFavorite?: () => void;
}

export default function TrailDetail({ trail, onClose, onTrailClick, isFavorite, onToggleFavorite }: TrailDetailProps) {
  const [photos, setPhotos] = useState<TrailPhoto[]>([]);
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [photoLoading, setPhotoLoading] = useState(true);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [elevationData, setElevationData] = useState<{ distance_mi: number; elev_ft: number }[]>([]);
  const [nearbyTrails, setNearbyTrails] = useState<Trail[]>([]);
  const [conditions, setConditions] = useState<ConditionReport[]>([]);
  const [wildlife, setWildlife] = useState<WildlifeObservation[]>([]);
  const [submittedCondition, setSubmittedCondition] = useState<string | null>(null);
  const [showToast, setShowToast] = useState(false);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(null);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [reviewRating, setReviewRating] = useState(0);
  const [reviewTitle, setReviewTitle] = useState("");
  const [reviewBody, setReviewBody] = useState("");
  const [reviewHikeDate, setReviewHikeDate] = useState("");
  const [reviewDiffFelt, setReviewDiffFelt] = useState("");
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [reviewsLimit, setReviewsLimit] = useState(5);
  const [bestDay, setBestDay] = useState<BestDayPrediction | null>(null);
  const [crowdPrediction, setCrowdPrediction] = useState<CrowdPrediction | null>(null);
  const [seasonalHeatmap, setSeasonalHeatmap] = useState<SeasonalHeatmap | null>(null);
  const [narrative, setNarrative] = useState<string | null>(null);
  const [narrativeLoading, setNarrativeLoading] = useState(false);
  const [npsAlerts, setNpsAlerts] = useState<NPSAlert[]>([]);
  const [sunTimes, setSunTimes] = useState<SunTimesResponse | null>(null);

  useEffect(() => {
    setPhotoLoading(true);
    fetchPhotos(trail.name, trail.nearby_city || "")
      .then((res) => setPhotos(res.photos))
      .catch(() => setPhotos([]))
      .finally(() => setPhotoLoading(false));
  }, [trail.name, trail.nearby_city]);

  useEffect(() => {
    if (!trail.lat || !trail.lng) return;
    setWeatherLoading(true);
    fetchWeather(trail.lat, trail.lng, trail.nearby_city || trail.name)
      .then(setWeather)
      .catch(() => setWeather(null))
      .finally(() => setWeatherLoading(false));
  }, [trail.lat, trail.lng, trail.nearby_city, trail.name]);

  useEffect(() => {
    if (trail.lat && trail.lng) {
      fetchWildlifeNearTrail(trail.lat, trail.lng, 2)
        .then(setWildlife)
        .catch(() => setWildlife([]));
    } else {
      setWildlife([]);
    }
  }, [trail.name, trail.lat, trail.lng]);

  useEffect(() => {
    if (trail.name) {
      fetchTrailConditions(trail.name)
        .then(setConditions)
        .catch(() => setConditions([]));
    } else {
      setConditions([]);
    }
  }, [trail.name]);

  useEffect(() => {
    if (trail.lat && trail.lng) {
      fetchNearbyTrails(trail.lat, trail.lng, 5, trail.name)
        .then(setNearbyTrails)
        .catch(() => setNearbyTrails([]));
    } else {
      setNearbyTrails([]);
    }
  }, [trail.name, trail.lat, trail.lng]);

  useEffect(() => {
    setElevationData([]);
    fetchGeometry([trail.name])
      .then((res) => {
        const t = res.trails[0];
        if (t?.elevation_profile?.length) {
          setElevationData(t.elevation_profile);
        }
      })
      .catch(() => {});
  }, [trail.name]);

  useEffect(() => {
    setReviews([]);
    setReviewSummary(null);
    setShowReviewForm(false);
    setReviewsLimit(5);
    fetchReviews(trail.name, 5).then(setReviews).catch(() => setReviews([]));
    fetchReviewSummary(trail.name).then(setReviewSummary).catch(() => setReviewSummary(null));
  }, [trail.name]);

  useEffect(() => {
    if (!trail.name) {
      setBestDay(null);
      return;
    }
    fetchBestDayPrediction(trail.name)
      .then(setBestDay)
      .catch(() => setBestDay(null));
  }, [trail.name]);

  useEffect(() => {
    if (!trail.name) {
      setCrowdPrediction(null);
      return;
    }
    fetchCrowdPrediction(trail.name)
      .then(setCrowdPrediction)
      .catch(() => setCrowdPrediction(null));
  }, [trail.name]);

  useEffect(() => {
    if (!trail.name) {
      setSeasonalHeatmap(null);
      return;
    }
    fetchSeasonalHeatmap(trail.name)
      .then(setSeasonalHeatmap)
      .catch(() => setSeasonalHeatmap(null));
  }, [trail.name]);

  useEffect(() => {
    if (trail.lat && trail.lng) {
      fetchSunTimes(trail.lat, trail.lng)
        .then((res) => setSunTimes(res.error ? null : res))
        .catch(() => setSunTimes(null));
    } else {
      setSunTimes(null);
    }
  }, [trail.lat, trail.lng]);

  useEffect(() => {
    const mgr = (trail.manager || "").toLowerCase();
    if (mgr.includes("national park") || mgr.includes("nps")) {
      fetchNPSAlerts("romo")
        .then((res) => setNpsAlerts(res.alerts))
        .catch(() => setNpsAlerts([]));
    } else {
      setNpsAlerts([]);
    }
  }, [trail.name, trail.manager]);

  useEffect(() => {
    setNarrative(null);
    setNarrativeLoading(true);
    const months = ["January","February","March","April","May","June","July","August","September","October","November","December"];
    const season = months[new Date().getMonth()];
    const weatherSummary = weather?.current
      ? `${Math.round(weather.current.temp_f)}°F, ${weather.current.weather_desc}, wind ${Math.round(weather.current.wind_mph)}mph`
      : "";
    fetchNarrative(trail.name, weatherSummary, season)
      .then((res) => setNarrative(res.narrative || null))
      .catch(() => setNarrative(null))
      .finally(() => setNarrativeLoading(false));
  }, [trail.name, weather]);

  const handleReviewSubmit = async () => {
    if (reviewRating === 0) return;
    setReviewSubmitting(true);
    const ok = await submitReview({
      trail_name: trail.name,
      rating: reviewRating,
      title: reviewTitle || undefined,
      body: reviewBody || undefined,
      hike_date: reviewHikeDate || undefined,
      difficulty_felt: reviewDiffFelt || undefined,
    });
    if (ok) {
      setShowReviewForm(false);
      setReviewRating(0);
      setReviewTitle("");
      setReviewBody("");
      setReviewHikeDate("");
      setReviewDiffFelt("");
      const [updatedReviews, updatedSummary] = await Promise.all([
        fetchReviews(trail.name, reviewsLimit),
        fetchReviewSummary(trail.name),
      ]);
      setReviews(updatedReviews);
      setReviewSummary(updatedSummary);
    }
    setReviewSubmitting(false);
  };

  const loadMoreReviews = async () => {
    const newLimit = reviewsLimit + 5;
    setReviewsLimit(newLimit);
    const more = await fetchReviews(trail.name, newLimit);
    setReviews(more);
  };

  const timeAgo = (dateStr: string): string => {
    const d = Date.now() - new Date(dateStr).getTime();
    const hours = Math.floor(d / 3600000);
    const days = Math.floor(hours / 24);
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    return "just now";
  };

  const getTaxonEmoji = (iconicTaxon: string): string =>
    ({
      Mammalia: "🦌",
      Aves: "🐦",
      Plantae: "🌿",
      Reptilia: "🦎",
      Amphibia: "🐸",
      Insecta: "🦋",
      Fungi: "🍄",
      Arachnida: "🕷️",
      Actinopterygii: "🐟",
    } as Record<string, string>)[iconicTaxon] ?? "🌿";

  const handleConditionSubmit = async (condition: string) => {
    setSubmittedCondition(condition);
    await submitTrailCondition(trail.name, condition);
    setShowToast(true);
    const updated = await fetchTrailConditions(trail.name);
    setConditions(updated);
    setTimeout(() => {
      setSubmittedCondition(null);
      setShowToast(false);
    }, 2500);
  };

  const diff = getDiffStyle(trail.difficulty);
  const estTime = estimateHikingTime(trail.length_miles, trail.elevation_gain_ft);
  const stars = trail.avg_rating
    ? "★".repeat(Math.round(trail.avg_rating)) + "☆".repeat(5 - Math.round(trail.avg_rating))
    : "";

  return (
    <div className="w-[340px] h-full bg-white border-l border-gray-200 flex flex-col z-20 shadow-xl">
      {/* Hero photo */}
      <div className="relative h-[170px] shrink-0 bg-gradient-to-br from-emerald-600 to-emerald-800 overflow-hidden">
        {photos.length > 0 ? (
          <img
            src={photos[0].thumb_url}
            alt={trail.name}
            className="w-full h-full object-cover"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Mountain className="w-12 h-12 text-white/40" />
          </div>
        )}
        <div className="absolute top-3 right-3 flex items-center gap-2">
          {onToggleFavorite && (
            <button
              onClick={onToggleFavorite}
              className="w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-black/60 transition-colors backdrop-blur-sm"
              title={isFavorite ? "Remove from saved" : "Save trail"}
            >
              <Heart className={`w-4 h-4 ${isFavorite ? "fill-red-500 text-red-500" : ""}`} />
            </button>
          )}
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-black/60 transition-colors backdrop-blur-sm"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-black/50 to-transparent" />
        <div className="absolute bottom-3 left-4 right-4">
          <h2 className="text-white font-bold text-[16px] leading-tight drop-shadow-md">
            {trail.name}
          </h2>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* Location + Rating */}
        <div className="px-4 pt-3 pb-2">
          {(trail.nearby_city || trail.location) && (
            <div className="flex items-center gap-1.5 text-[12px] text-gray-500 mb-2">
              <MapPin className="w-3.5 h-3.5 text-gray-400" />
              {trail.nearby_city}{trail.location ? `, ${trail.location.split(",")[0]}` : ""}
            </div>
          )}
          {stars && (
            <div className="flex items-center gap-1.5 mb-2">
              <span className="text-amber-500 text-sm">{stars}</span>
              <span className="text-[11px] text-gray-400">({trail.review_count} reviews)</span>
            </div>
          )}
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ${diff.bg} ${diff.text}`}>
            <span className={`w-2 h-2 rounded-full ${diff.dot}`} />
            {diff.label}
          </span>
          {(() => {
            const adj = adjustDifficulty(trail.difficulty, weather);
            if (!adj) return null;
            return (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-800 border border-amber-300 ml-1">
                ⚠️ {adj.adjusted} — {adj.reason}
              </span>
            );
          })()}

          {trail.trailblaze_score != null && (
            <div
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold mt-2 ${
                trail.trailblaze_score >= 80
                  ? "bg-green-50 text-green-700 border border-green-200"
                  : trail.trailblaze_score >= 60
                    ? "bg-amber-50 text-amber-700 border border-amber-200"
                    : "bg-red-50 text-red-700 border border-red-200"
              }`}
              title="TrailBlaze Score combines trail quality, community feedback, weather safety, and source reliability"
            >
              <span>⭐</span>
              <span>{trail.trailblaze_score.toFixed(1)} TrailBlaze Score</span>
            </div>
          )}

          {trail.hp_rating != null && trail.hp_rating > 0 && (
            <div className="flex items-center gap-2 mt-2">
              <div className="flex items-center gap-0.5">
                {[1,2,3,4,5].map((star) => (
                  <svg
                    key={star}
                    className={`w-3.5 h-3.5 ${
                      star <= Math.round(trail.hp_rating!)
                        ? "text-amber-400"
                        : "text-gray-300"
                    }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>
              <span className="text-amber-500 text-xs font-semibold">
                {trail.hp_rating.toFixed(1)}
              </span>
              <span className="text-gray-400 text-[10px]">
                REI Hiking Project
              </span>
            </div>
          )}

          {trail.hp_summary && (
            <p className="text-gray-500 text-[11px] mt-2 leading-relaxed">
              {trail.hp_summary}
            </p>
          )}

          {trail.hp_condition && trail.hp_condition !== "Unknown" && (
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-50 border border-gray-200 mt-2">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />
              <span className="text-[10px] text-gray-600">
                {trail.hp_condition}
              </span>
            </div>
          )}
        </div>

        {/* AI Trail Narrator */}
        {narrativeLoading && (
          <div className="px-4 py-2">
            <div className="bg-indigo-50 rounded-xl p-3 border border-indigo-100 animate-pulse">
              <div className="h-3 bg-indigo-200/50 rounded w-2/3 mb-2" />
              <div className="h-3 bg-indigo-200/50 rounded w-full" />
            </div>
          </div>
        )}
        {!narrativeLoading && narrative && (
          <div className="px-4 py-2">
            <div className="bg-indigo-50 rounded-xl p-3 border border-indigo-100">
              <p className="text-[10px] text-indigo-400 font-semibold mb-1">🤖 AI Preview</p>
              <p className="text-[11px] text-indigo-800 leading-relaxed italic">{narrative}</p>
            </div>
          </div>
        )}

        {/* Stats grid */}
        <div className="px-4 py-2 grid grid-cols-2 gap-2">
          <div className="bg-gray-50 rounded-xl p-2.5 text-center">
            <Ruler className="w-4 h-4 text-gray-400 mx-auto mb-0.5" />
            <div className="text-[14px] font-bold text-gray-800">
              {trail.length_miles ? `${trail.length_miles} mi` : "—"}
            </div>
            <div className="text-[9px] text-gray-400 uppercase">Distance</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-2.5 text-center">
            <Clock className="w-4 h-4 text-gray-400 mx-auto mb-0.5" />
            <div className="text-[14px] font-bold text-gray-800">{estTime}</div>
            <div className="text-[9px] text-gray-400 uppercase">Est. Time</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-2.5 text-center">
            <TrendingUp className="w-4 h-4 text-gray-400 mx-auto mb-0.5" />
            <div className="text-[14px] font-bold text-gray-800">
              {trail.elevation_gain_ft ? `${Math.round(trail.elevation_gain_ft)} ft` : "—"}
            </div>
            <div className="text-[9px] text-gray-400 uppercase">Elev. Gain</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-2.5 text-center">
            <Footprints className="w-4 h-4 text-gray-400 mx-auto mb-0.5" />
            <div className="text-[14px] font-bold text-gray-800 capitalize">{trail.surface || "—"}</div>
            <div className="text-[9px] text-gray-400 uppercase">Surface</div>
          </div>
        </div>

        {/* Elevation Profile */}
        <ElevationProfile data={elevationData} trailName={trail.name} />

        {/* Current Weather */}
        {weatherLoading && (
          <div className="px-4 py-2">
            <div className="bg-blue-50 rounded-xl p-3 border border-blue-100 animate-pulse">
              <div className="h-4 bg-blue-200/50 rounded w-1/3 mb-2" />
              <div className="h-8 bg-blue-200/50 rounded w-1/2" />
            </div>
          </div>
        )}
        {!weatherLoading && !weather?.current && trail.lat && trail.lng && (
          <div className="px-4 py-2">
            <div className="bg-amber-50 rounded-xl px-3 py-2.5 border border-amber-200 text-[11px] text-amber-700">
              ⚠️ Weather data temporarily unavailable. Please try again later.
            </div>
          </div>
        )}
        {!weatherLoading && !trail.lat && (
          <div className="px-4 py-2">
            <div className="bg-gray-50 rounded-xl px-3 py-2.5 border border-gray-200 text-[11px] text-gray-500">
              📍 Location data not available — weather cannot be loaded for this trail.
            </div>
          </div>
        )}
        {weather?.current && (
          <div className="px-4 py-2">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Current Weather
            </p>
            <div className="bg-gradient-to-br from-blue-50 to-sky-50 rounded-xl p-3 border border-blue-100">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{weather.current.weather_icon}</span>
                  <div>
                    <div className="text-[18px] font-bold text-gray-800">
                      {Math.round(weather.current.temp_f)}°F
                    </div>
                    <div className="text-[10px] text-gray-500">
                      Feels {Math.round(weather.current.feels_like_f)}°F
                    </div>
                  </div>
                </div>
                <div className="text-right text-[11px] text-gray-600">
                  {weather.current.weather_desc}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center text-[10px]">
                <div className="flex flex-col items-center gap-0.5">
                  <Wind className="w-3.5 h-3.5 text-blue-400" />
                  <span className="font-semibold text-gray-700">{Math.round(weather.current.wind_mph)} mph</span>
                  <span className="text-gray-400">Wind</span>
                </div>
                <div className="flex flex-col items-center gap-0.5">
                  <Droplets className="w-3.5 h-3.5 text-blue-400" />
                  <span className="font-semibold text-gray-700">{Math.round(weather.current.humidity_pct)}%</span>
                  <span className="text-gray-400">Humidity</span>
                </div>
                <div className="flex flex-col items-center gap-0.5">
                  <Sun className="w-3.5 h-3.5 text-amber-400" />
                  <span className="font-semibold text-gray-700">{weather.current.uv_index.toFixed(0)}</span>
                  <span className="text-gray-400">UV Index</span>
                </div>
              </div>
              {(() => {
                const safety = weatherSafetyScore(weather.current);
                return (
                  <div className="mt-2 flex items-center justify-center gap-1.5">
                    <span className={`text-[11px] font-bold ${safety.color}`}>
                      Safety: {safety.label} {safety.score}
                    </span>
                  </div>
                );
              })()}
            </div>
          </div>
        )}

        {/* Hiking Advisory */}
        {weather?.hiking_advisory && (
          <div className="px-4 py-1">
            <div className={`rounded-lg px-3 py-2 text-[11px] leading-relaxed ${
              weather.hiking_advisory.startsWith("✅")
                ? "bg-green-50 text-green-700 border border-green-200"
                : weather.hiking_advisory.startsWith("⚠️") || weather.hiking_advisory.startsWith("⛈️")
                  ? "bg-red-50 text-red-700 border border-red-200"
                  : "bg-amber-50 text-amber-700 border border-amber-200"
            }`}>
              {weather.hiking_advisory}
            </div>
          </div>
        )}

        {/* Sunrise / Sunset */}
        {sunTimes && (sunTimes.sunrise || sunTimes.sunset) && (
          <div className="px-4 py-2">
            <div className="bg-amber-50 rounded-xl p-3 border border-amber-100">
              <p className="text-[10px] text-amber-500 font-semibold mb-1.5">☀️ Daylight</p>
              <div className="grid grid-cols-3 gap-2 text-center text-[10px]">
                {sunTimes.sunrise && (
                  <div>
                    <p className="text-amber-600 font-semibold">🌅 Sunrise</p>
                    <p className="text-gray-700 font-medium">
                      {new Date(sunTimes.sunrise).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                )}
                {sunTimes.sunset && (
                  <div>
                    <p className="text-amber-600 font-semibold">🌇 Sunset</p>
                    <p className="text-gray-700 font-medium">
                      {new Date(sunTimes.sunset).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                )}
                {sunTimes.day_length && (
                  <div>
                    <p className="text-amber-600 font-semibold">⏱ Day</p>
                    <p className="text-gray-700 font-medium">
                      {(() => {
                        const secs = parseInt(sunTimes.day_length || "0", 10);
                        if (!secs) return sunTimes.day_length;
                        const h = Math.floor(secs / 3600);
                        const m = Math.floor((secs % 3600) / 60);
                        return `${h}h ${m}m`;
                      })()}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* NPS Park Alerts */}
        {npsAlerts.length > 0 && (
          <div className="px-4 py-2">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              NPS Park Alerts
            </p>
            <div className="space-y-1.5">
              {npsAlerts.slice(0, 3).map((alert, i) => (
                <div
                  key={i}
                  className={`rounded-lg px-3 py-2 text-[11px] leading-relaxed border ${
                    alert.category === "Danger"
                      ? "bg-red-50 text-red-700 border-red-200"
                      : alert.category === "Caution"
                        ? "bg-amber-50 text-amber-700 border-amber-200"
                        : "bg-blue-50 text-blue-700 border-blue-200"
                  }`}
                >
                  <p className="font-semibold">{alert.title}</p>
                  <p className="mt-0.5 line-clamp-2">{alert.description}</p>
                  {alert.url && (
                    <a
                      href={alert.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block mt-1 text-[10px] underline"
                    >
                      More info →
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Crowd Prediction */}
        {crowdPrediction && (
          <div className="px-4 py-1">
            <div className="bg-violet-50 border border-violet-200 rounded-lg px-3 py-2 text-[11px] text-violet-800 leading-relaxed">
              👥 Expected {formatDay(crowdPrediction.target_date)}: <span className="font-semibold">{crowdPrediction.level}</span>
              {" · "}Best time: {crowdPrediction.best_time}
            </div>
            {crowdPrediction.weekly_forecast.length > 0 && (
              <div className="mt-2 grid grid-cols-7 gap-1">
                {crowdPrediction.weekly_forecast.map((d) => (
                  <div key={d.date} className="text-center">
                    <div className="text-[9px] text-gray-400 mb-1 truncate">{formatDay(d.date).slice(0, 3)}</div>
                    <div className="h-8 rounded bg-gray-100 relative overflow-hidden">
                      <div
                        className={`absolute bottom-0 w-full ${
                          d.score >= 75 ? "bg-red-400" :
                          d.score >= 50 ? "bg-amber-400" :
                          d.score >= 25 ? "bg-yellow-300" :
                          "bg-green-400"
                        }`}
                        style={{ height: `${Math.max(12, d.score)}%` }}
                      />
                    </div>
                    <div className="text-[9px] text-gray-500 mt-0.5">{d.score}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Safety Notes */}
        {weather?.safety_notes && weather.safety_notes.length > 0 && (
          <div className="px-4 py-1">
            {weather.safety_notes.map((note, i) => (
              <div key={i} className="flex items-start gap-1.5 text-[10px] text-orange-600 mb-1">
                <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                <span>{note}</span>
              </div>
            ))}
          </div>
        )}

        {/* 4-Day Forecast */}
        {weather?.forecast && weather.forecast.length > 0 && (
          <div className="px-4 py-2">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              4-Day Forecast
            </p>
            <div className="space-y-1.5">
              {weather.forecast.map((day, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-lg">{day.weather_icon}</span>
                    <div className="min-w-0">
                      <div className="text-[11px] font-semibold text-gray-700 truncate">
                        {formatDay(day.date)}
                      </div>
                      <div className="text-[9px] text-gray-400 truncate">{day.weather_desc}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0 text-[11px]">
                    {day.snowfall_sum_in > 0 && (
                      <span className="flex items-center gap-0.5 text-blue-500">
                        <CloudSnow className="w-3 h-3" />{day.snowfall_sum_in.toFixed(1)}"
                      </span>
                    )}
                    {day.precipitation_prob > 0 && (
                      <span className="flex items-center gap-0.5 text-blue-400">
                        <Droplets className="w-3 h-3" />{day.precipitation_prob}%
                      </span>
                    )}
                    <div className="text-right">
                      <span className="font-bold text-gray-700">{Math.round(day.temp_high_f)}°</span>
                      <span className="text-gray-400 mx-0.5">/</span>
                      <span className="text-gray-400">{Math.round(day.temp_low_f)}°</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Seasonal Heatmap */}
        {seasonalHeatmap && (
          <div className="px-4 py-2">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Seasonal Heatmap
            </p>
            <div className="grid grid-cols-12 gap-1 mb-2">
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => {
                const score = seasonalHeatmap.monthly_scores[String(m)] ?? 0;
                const color =
                  score >= 75 ? "bg-green-400" :
                  score >= 45 ? "bg-amber-300" :
                  "bg-red-300";
                return (
                  <div key={m} className="text-center">
                    <div className={`h-8 rounded ${color} border border-white/70`} title={`${monthLabel(m)}: ${score}`} />
                    <div className="text-[8px] text-gray-400 mt-0.5">{monthLabel(m).slice(0, 1)}</div>
                  </div>
                );
              })}
            </div>
            <p className="text-[10px] text-gray-500">
              Best months: <span className="font-semibold text-green-700">{seasonalHeatmap.best_months.map(monthLabel).join(" — ")}</span>
              {" · "}
              Avoid: <span className="font-semibold text-red-600">{seasonalHeatmap.worst_months.map(monthLabel).join(" — ")}</span>
            </p>
          </div>
        )}

        {/* Best Day Predictor */}
        {bestDay && (
          <div className="px-4 py-1">
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-[11px] text-emerald-700 leading-relaxed">
              📅 Best day this week: <span className="font-semibold">{formatDay(bestDay.best_date)}</span>
              {" — "}{bestDay.reason}
            </div>
          </div>
        )}

        {/* Trail Conditions Section */}
        <div className="px-4 py-2">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Report Trail Conditions
          </p>

          {conditions.length > 0 && (
            <div className="text-xs text-gray-500 mb-2 bg-gray-50 rounded-lg px-3 py-2 border border-gray-200">
              <span className="text-gray-400">Last report: </span>
              <span className="text-gray-700 font-medium">
                {conditions[0].condition}
              </span>
              <span className="text-gray-400">
                {" · "}{timeAgo(conditions[0].reported_at)}
              </span>
              {conditions[0].note && (
                <p className="text-gray-400 mt-1 italic text-[11px]">
                  "{conditions[0].note}"
                </p>
              )}
            </div>
          )}

          <div className="grid grid-cols-3 gap-1.5">
            {([
              { label: "Clear", emoji: "✅", color: "text-green-600" },
              { label: "Muddy", emoji: "💧", color: "text-blue-500" },
              { label: "Snow", emoji: "❄️", color: "text-sky-500" },
              { label: "Icy", emoji: "🧊", color: "text-cyan-500" },
              { label: "Downed Tree", emoji: "🌲", color: "text-amber-600" },
              { label: "Washed Out", emoji: "🌊", color: "text-red-500" },
            ] as const).map(({ label, emoji, color }) => (
              <button
                key={label}
                onClick={() => handleConditionSubmit(label)}
                className={`flex flex-col items-center py-2 px-1 rounded-xl bg-gray-50 border transition-all duration-150 text-center cursor-pointer select-none ${
                  submittedCondition === label
                    ? "border-green-500 bg-green-50 scale-95"
                    : "border-gray-200 hover:border-gray-400"
                }`}
              >
                <span className="text-base leading-none mb-1">{emoji}</span>
                <span className={`text-[10px] ${color} leading-tight`}>{label}</span>
              </button>
            ))}
          </div>

          {showToast && (
            <p className="text-center text-[11px] text-green-600 mt-2 animate-pulse">
              Thanks for reporting! ✓
            </p>
          )}
        </div>

        {/* Additional info */}
        <div className="px-4 py-2 space-y-1.5">
          {trail.dogs && (
            <div className="flex items-center gap-2 text-[12px] text-gray-600">
              <Dog className="w-4 h-4 text-gray-400" />
              <span>Dogs: {trail.dogs}</span>
            </div>
          )}
          {trail.manager && (
            <div className="flex items-center gap-2 text-[12px] text-gray-500">
              <Mountain className="w-4 h-4 text-gray-400" />
              <span className="truncate">{trail.manager}</span>
            </div>
          )}
        </div>

        {/* Photo gallery */}
        {photos.length > 1 && (
          <div className="px-4 py-2">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Photos
            </p>
            <div className="grid grid-cols-2 gap-1.5">
              {photos.slice(1, 5).map((p, i) => (
                <div
                  key={i}
                  className="h-[65px] rounded-lg overflow-hidden cursor-pointer bg-gray-100"
                  onClick={() => window.open(p.url, "_blank")}
                >
                  <img
                    src={p.thumb_url}
                    alt={p.title}
                    className="w-full h-full object-cover hover:scale-105 transition-transform duration-200"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Nearby Trails */}
        {nearbyTrails.length > 0 && (
          <div className="px-4 py-2">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Nearby Trails
            </p>
            <div className="flex gap-2.5 overflow-x-auto pb-2 scrollbar-hide">
              {nearbyTrails.map((t) => (
                <button
                  key={t.name}
                  onClick={() => onTrailClick?.({
                    name: t.name,
                    difficulty: t.difficulty,
                    length_miles: t.length_miles,
                    elevation_gain_ft: t.elevation_gain_ft,
                    manager: t.manager,
                    review_count: 0,
                  })}
                  className="flex-shrink-0 w-36 bg-gray-50 rounded-xl p-2.5 border border-gray-200 hover:border-emerald-400 text-left transition-colors cursor-pointer"
                >
                  <p className="text-gray-800 text-xs font-medium leading-tight line-clamp-2 mb-1">
                    {t.name}
                  </p>
                  <p className={`text-[10px] font-semibold ${
                    t.difficulty === 'easy' ? 'text-green-600' :
                    t.difficulty === 'hard' ? 'text-red-500' :
                    'text-amber-600'
                  }`}>
                    {t.difficulty ? t.difficulty.charAt(0).toUpperCase() + t.difficulty.slice(1) : 'Unknown'}
                  </p>
                  <p className="text-gray-400 text-[10px] mt-0.5">
                    {(t as any).distance_from_here_miles
                      ? `${(t as any).distance_from_here_miles} mi away`
                      : ''}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Wildlife Spotted Nearby */}
        {wildlife.length > 0 && (
          <div className="px-4 py-2">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                Wildlife Spotted Nearby
              </p>
              <span className="text-[9px] text-gray-300">iNaturalist</span>
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {wildlife.map((obs, i) => (
                <div
                  key={i}
                  className="bg-gray-50 rounded-xl p-2 border border-gray-200 text-center"
                >
                  {obs.photo_url ? (
                    <img
                      src={obs.photo_url}
                      alt={obs.name}
                      className="w-full h-14 object-cover rounded-lg mb-1.5"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <div className="w-full h-14 flex items-center justify-center text-2xl mb-1.5">
                      {getTaxonEmoji(obs.iconic_taxon)}
                    </div>
                  )}
                  <p className="text-gray-700 text-[10px] font-medium leading-tight line-clamp-2">
                    {obs.name}
                  </p>
                  <p className="text-gray-400 text-[9px] mt-0.5 italic truncate">
                    {obs.scientific}
                  </p>
                </div>
              ))}
            </div>
            <p className="text-[9px] text-gray-300 mt-1.5 text-center">
              Research-grade · within 2 miles
            </p>
          </div>
        )}

        {/* Reviews Section */}
        <div className="px-4 py-2 border-t border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
              Reviews
            </p>
            <button
              onClick={() => setShowReviewForm(!showReviewForm)}
              className="text-[10px] font-semibold text-emerald-600 hover:text-emerald-700 cursor-pointer"
            >
              {showReviewForm ? "Cancel" : "+ Write Review"}
            </button>
          </div>

          {/* Review Summary */}
          {reviewSummary && reviewSummary.total_reviews > 0 && (
            <div className="bg-gray-50 rounded-xl p-3 border border-gray-200 mb-2">
              <div className="flex items-center gap-2 mb-1.5">
                <div className="flex items-center gap-0.5">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <svg
                      key={s}
                      className={`w-3.5 h-3.5 ${
                        s <= Math.round(reviewSummary.average_rating)
                          ? "text-amber-400"
                          : "text-gray-300"
                      }`}
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                </div>
                <span className="text-xs font-bold text-gray-800">
                  {reviewSummary.average_rating.toFixed(1)}
                </span>
                <span className="text-[10px] text-gray-400">
                  ({reviewSummary.total_reviews} review{reviewSummary.total_reviews !== 1 ? "s" : ""})
                </span>
              </div>
              {/* Rating bars */}
              <div className="space-y-0.5">
                {[5, 4, 3, 2, 1].map((n) => {
                  const count = reviewSummary.rating_breakdown[n] || 0;
                  const pct = reviewSummary.total_reviews > 0
                    ? (count / reviewSummary.total_reviews) * 100
                    : 0;
                  return (
                    <div key={n} className="flex items-center gap-1.5 text-[9px]">
                      <span className="text-gray-400 w-2 text-right">{n}</span>
                      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-amber-400 rounded-full"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-gray-400 w-4 text-right">{count}</span>
                    </div>
                  );
                })}
              </div>
              {/* Difficulty breakdown */}
              {(reviewSummary.difficulty_breakdown.easier > 0 ||
                reviewSummary.difficulty_breakdown.harder > 0) && (
                <div className="flex gap-2 mt-2 text-[9px]">
                  {reviewSummary.difficulty_breakdown.easier > 0 && (
                    <span className="text-green-600">
                      ↓ {reviewSummary.difficulty_breakdown.easier} said easier
                    </span>
                  )}
                  {reviewSummary.difficulty_breakdown.as_expected > 0 && (
                    <span className="text-gray-500">
                      = {reviewSummary.difficulty_breakdown.as_expected} as expected
                    </span>
                  )}
                  {reviewSummary.difficulty_breakdown.harder > 0 && (
                    <span className="text-red-500">
                      ↑ {reviewSummary.difficulty_breakdown.harder} said harder
                    </span>
                  )}
                </div>
              )}

              {reviewSummary.sentiment_summary &&
                Object.keys(reviewSummary.sentiment_summary.themes || {}).length > 0 && (
                  <div className="mt-2 space-y-1.5">
                    <div className="text-[9px] text-gray-500 font-medium">
                      😊 {reviewSummary.sentiment_summary.positive_pct}% positive review sentiment
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(reviewSummary.sentiment_summary.themes)
                        .slice(0, 3)
                        .map(([theme, count]) => (
                          <span
                            key={theme}
                            className="inline-flex items-center px-2 py-0.5 rounded-full bg-white border border-gray-200 text-[9px] text-gray-600"
                          >
                            {getSentimentThemeDisplay(theme, count)}
                          </span>
                        ))}
                    </div>
                  </div>
                )}
            </div>
          )}

          {reviewSummary && reviewSummary.total_reviews === 0 && !showReviewForm && (
            <p className="text-[11px] text-gray-400 mb-2">
              No reviews yet. Be the first to review this trail!
            </p>
          )}

          {/* Review Form */}
          {showReviewForm && (
            <div className="bg-emerald-50 rounded-xl p-3 border border-emerald-200 mb-2 space-y-2">
              {/* Star rating */}
              <div>
                <p className="text-[10px] text-gray-500 mb-1">Rating *</p>
                <div className="flex gap-0.5">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <button
                      key={s}
                      onClick={() => setReviewRating(s)}
                      className="cursor-pointer"
                    >
                      <svg
                        className={`w-6 h-6 ${
                          s <= reviewRating ? "text-amber-400" : "text-gray-300"
                        } hover:text-amber-400 transition-colors`}
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                    </button>
                  ))}
                </div>
              </div>
              {/* Title */}
              <input
                type="text"
                placeholder="Title (optional)"
                maxLength={80}
                value={reviewTitle}
                onChange={(e) => setReviewTitle(e.target.value)}
                className="w-full text-xs bg-white rounded-lg border border-gray-200 px-2.5 py-1.5 focus:outline-none focus:border-emerald-400"
              />
              {/* Body */}
              <textarea
                placeholder="Share your experience... (optional)"
                maxLength={500}
                rows={3}
                value={reviewBody}
                onChange={(e) => setReviewBody(e.target.value)}
                className="w-full text-xs bg-white rounded-lg border border-gray-200 px-2.5 py-1.5 focus:outline-none focus:border-emerald-400 resize-none"
              />
              <div className="flex gap-2">
                {/* Hike date */}
                <input
                  type="date"
                  value={reviewHikeDate}
                  onChange={(e) => setReviewHikeDate(e.target.value)}
                  className="flex-1 text-[10px] bg-white rounded-lg border border-gray-200 px-2 py-1.5 focus:outline-none focus:border-emerald-400"
                />
                {/* Difficulty felt */}
                <select
                  value={reviewDiffFelt}
                  onChange={(e) => setReviewDiffFelt(e.target.value)}
                  className="flex-1 text-[10px] bg-white rounded-lg border border-gray-200 px-2 py-1.5 focus:outline-none focus:border-emerald-400"
                >
                  <option value="">Difficulty felt?</option>
                  <option value="Easier than expected">Easier</option>
                  <option value="As expected">As expected</option>
                  <option value="Harder than expected">Harder</option>
                </select>
              </div>
              <button
                onClick={handleReviewSubmit}
                disabled={reviewRating === 0 || reviewSubmitting}
                className={`w-full text-xs font-semibold py-2 rounded-lg transition-colors ${
                  reviewRating === 0
                    ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                    : "bg-emerald-600 text-white hover:bg-emerald-700 cursor-pointer"
                }`}
              >
                {reviewSubmitting ? "Submitting..." : "Submit Review"}
              </button>
            </div>
          )}

          {/* Reviews List */}
          {reviews.length > 0 && (
            <div className="space-y-1.5">
              {reviews.map((r) => (
                <div
                  key={r.id}
                  className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-200"
                >
                  <div className="flex items-center justify-between mb-0.5">
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map((s) => (
                        <svg
                          key={s}
                          className={`w-2.5 h-2.5 ${
                            s <= r.rating ? "text-amber-400" : "text-gray-300"
                          }`}
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                      ))}
                    </div>
                    <span className="text-[9px] text-gray-400">
                      {timeAgo(r.reported_at)}
                    </span>
                  </div>
                  {r.title && (
                    <p className="text-[11px] font-semibold text-gray-700">
                      {r.title}
                    </p>
                  )}
                  {r.body && (
                    <p className="text-[11px] text-gray-600 leading-relaxed mt-0.5">
                      {r.body}
                    </p>
                  )}
                  <div className="flex gap-2 mt-1 text-[9px] text-gray-400">
                    {r.hike_date && <span>Hiked: {r.hike_date}</span>}
                    {r.difficulty_felt && <span>· {r.difficulty_felt}</span>}
                  </div>
                </div>
              ))}
              {reviewSummary && reviews.length < reviewSummary.total_reviews && (
                <button
                  onClick={loadMoreReviews}
                  className="w-full text-[10px] text-emerald-600 font-semibold hover:text-emerald-700 py-1.5 cursor-pointer"
                >
                  Show more reviews
                </button>
              )}
            </div>
          )}
        </div>

        {/* Route info */}
        <div className="px-4 py-2 border-t border-gray-100">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Route Info
          </p>
          <div className="text-[12px] text-gray-600 space-y-1">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <ArrowUpRight className="w-3.5 h-3.5 text-emerald-500" />
                Trail type
              </span>
              <span className="font-medium text-gray-700">{trail.surface === "paved" ? "Paved" : "Trail"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <ArrowDownRight className="w-3.5 h-3.5 text-blue-500" />
                Route style
              </span>
              <span className="font-medium text-gray-700">Out & back</span>
            </div>
          </div>
          <button
            onClick={() => window.open(`/gpx-preview?trail=${encodeURIComponent(trail.name)}`, "_blank")}
            className="mt-2 w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-lg border border-emerald-200 hover:bg-emerald-100 transition-colors cursor-pointer"
          >
            ⬇ Download GPX
          </button>
        </div>

        <div className="h-4" />
      </div>
    </div>
  );
}
