"use client";

import { useEffect, useState } from "react";
import { Mountain, MapPin, Ruler, CloudSun, Heart } from "lucide-react";
import { fetchPhotos, fetchReviewSummary, type TrailReference, type ReviewSummary } from "@/lib/api";

function getDiffStyle(d?: string) {
  switch (d) {
    case "easy": return { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500" };
    case "moderate": return { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" };
    case "hard": return { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" };
    default: return { bg: "bg-gray-50", text: "text-gray-600", dot: "bg-gray-400" };
  }
}

interface FitnessProfile {
  fitness_level: "beginner" | "intermediate" | "advanced";
  max_distance_miles: number;
  max_elevation_gain_ft: number;
  pace_min_per_mile: number;
  preferred_surface: "any" | "paved" | "dirt" | "gravel";
}

function matchesFitnessProfile(trail: TrailReference, profile: FitnessProfile): boolean {
  if (trail.length_miles && trail.length_miles > profile.max_distance_miles) return false;
  if (trail.elevation_gain_ft && trail.elevation_gain_ft > profile.max_elevation_gain_ft) return false;
  if (
    profile.preferred_surface !== "any" &&
    trail.surface &&
    !trail.surface.toLowerCase().includes(profile.preferred_surface)
  ) return false;
  return true;
}

function estimateHikeTime(trail: TrailReference, paceMinPerMile: number): string | null {
  if (!trail.length_miles) return null;
  const walkMin = trail.length_miles * paceMinPerMile;
  const elevMin = (trail.elevation_gain_ft || 0) / 1000 * 15;
  const totalMin = Math.round(walkMin + elevMin);
  const hrs = Math.floor(totalMin / 60);
  const mins = totalMin % 60;
  if (hrs > 0 && mins > 0) return `~${hrs}h ${mins}m at your pace`;
  if (hrs > 0) return `~${hrs}h at your pace`;
  return `~${mins}m at your pace`;
}

interface TrailCardsProps {
  trails: TrailReference[];
  weatherContext?: string;
  title?: string;
  onTrailClick?: (trail: TrailReference) => void;
  fitnessProfile?: FitnessProfile;
  favorites?: string[];
  onToggleFavorite?: (name: string) => void;
}

export default function TrailCards({ trails, weatherContext, title, onTrailClick, fitnessProfile, favorites, onToggleFavorite }: TrailCardsProps) {
  const [photos, setPhotos] = useState<Record<string, string>>({});
  const [ratings, setRatings] = useState<Record<string, ReviewSummary>>({});
  const [sortMode, setSortMode] = useState<"default" | "trailblaze_score">("default");

  useEffect(() => {
    // Only fetch photos for the first 10 to avoid overloading
    const toFetch = trails.slice(0, 10);
    toFetch.forEach((t) => {
      if (photos[t.name]) return;
      fetchPhotos(t.name, t.nearby_city || "")
        .then((res) => {
          if (res.photos.length > 0) {
            setPhotos((prev) => ({ ...prev, [t.name]: res.photos[0].thumb_url }));
          }
        })
        .catch(() => {});
    });
  }, [trails]);

  useEffect(() => {
    const toFetch = trails.slice(0, 10);
    toFetch.forEach((t) => {
      if (ratings[t.name]) return;
      fetchReviewSummary(t.name)
        .then((summary) => {
          if (summary && summary.total_reviews > 0) {
            setRatings((prev) => ({ ...prev, [t.name]: summary }));
          }
        })
        .catch(() => {});
    });
  }, [trails]);

  if (trails.length === 0) return null;

  const displayedTrails = [...trails];
  if (sortMode === "trailblaze_score") {
    displayedTrails.sort(
      (a, b) => (b.trailblaze_score ?? -1) - (a.trailblaze_score ?? -1)
    );
  }

  return (
    <div className="bg-white">
      {/* Weather banner */}
      {weatherContext && (
        <div className="px-4 py-2.5 bg-gradient-to-r from-sky-50 to-blue-50 border-b border-sky-100 flex items-start gap-2">
          <CloudSun className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
          <p className="text-xs text-sky-800 leading-relaxed line-clamp-2">{weatherContext}</p>
        </div>
      )}

      {/* Trail cards */}
      <div className="px-3 py-2">
        {(title || trails.some((t) => t.trailblaze_score != null)) && (
          <div className="flex items-center justify-between mb-2 px-1">
            {title ? (
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                {title}
              </p>
            ) : <span />}
            {trails.some((t) => t.trailblaze_score != null) && (
              <button
                onClick={() => setSortMode((m) => m === "default" ? "trailblaze_score" : "default")}
                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border transition-colors cursor-pointer ${
                  sortMode === "trailblaze_score"
                    ? "bg-emerald-600 text-white border-emerald-600"
                    : "bg-gray-50 text-gray-500 border-gray-200 hover:border-gray-300"
                }`}
              >
                {sortMode === "trailblaze_score" ? "Sorted: Score" : "Sort by Score"}
              </button>
            )}
          </div>
        )}
        <div className="space-y-1.5">
          {displayedTrails.map((t, i) => {
            const diff = getDiffStyle(t.difficulty);
            const photoUrl = photos[t.name];
            const rating = ratings[t.name];
            const matches = fitnessProfile ? matchesFitnessProfile(t, fitnessProfile) : null;
            const hikeTime = fitnessProfile ? estimateHikeTime(t, fitnessProfile.pace_min_per_mile) : null;
            return (
              <div
                key={`${t.name}-${i}`}
                onClick={() => onTrailClick?.(t)}
                className={`flex gap-2.5 bg-white rounded-xl p-2 border border-gray-100 cursor-pointer hover:shadow-md hover:border-emerald-200 transition-all group ${
                  matches === false ? "opacity-40" : ""
                }`}
              >
                {/* Photo */}
                <div className="w-[72px] h-[72px] rounded-lg overflow-hidden shrink-0 bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center">
                  {photoUrl ? (
                    <img
                      src={photoUrl}
                      alt={t.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <Mountain className="w-5 h-5 text-white/80" />
                  )}
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0 py-0.5">
                  <h3 className="text-[13px] font-semibold text-gray-800 truncate group-hover:text-emerald-700 transition-colors">
                    {t.name}
                  </h3>
                  {(t.location || t.nearby_city) && (
                    <div className="flex items-center gap-1 mt-0.5">
                      <MapPin className="w-3 h-3 text-gray-400" />
                      <span className="text-[10px] text-gray-400 truncate">
                        {t.nearby_city || t.location}
                      </span>
                    </div>
                  )}
                  {rating && (
                    <div className="flex items-center gap-1 mt-0.5">
                      <div className="flex items-center gap-px">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <svg
                            key={s}
                            className={`w-2.5 h-2.5 ${
                              s <= Math.round(rating.average_rating)
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
                      <span className="text-[9px] text-gray-400">
                        ({rating.total_reviews})
                      </span>
                    </div>
                  )}
                  {t.trailblaze_score != null && (
                    <div className="inline-flex items-center gap-1 mt-1 px-1.5 py-0.5 rounded-full bg-indigo-50 border border-indigo-200 text-[10px] font-semibold text-indigo-700">
                      <span>⭐</span>
                      <span>{t.trailblaze_score.toFixed(1)} TrailBlaze</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                    {onToggleFavorite && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onToggleFavorite(t.name); }}
                        className="p-0.5 rounded-full hover:bg-red-50 transition-colors"
                        title={favorites?.includes(t.name) ? "Remove from saved" : "Save trail"}
                      >
                        <Heart className={`w-3.5 h-3.5 ${favorites?.includes(t.name) ? "fill-red-500 text-red-500" : "text-gray-300 hover:text-red-400"}`} />
                      </button>
                    )}
                    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${diff.bg} ${diff.text}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${diff.dot}`} />
                      {t.difficulty || "Unknown"}
                    </span>
                    {t.length_miles && (
                      <span className="inline-flex items-center gap-0.5 text-[10px] text-gray-500">
                        <Ruler className="w-3 h-3" />
                        {t.length_miles} mi
                      </span>
                    )}
                    {matches === true && (
                      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-green-50 text-green-700">
                        ✓ Matches your profile
                      </span>
                    )}
                    {matches === false && (
                      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-500">
                        Outside your level
                      </span>
                    )}
                  </div>
                  {hikeTime && matches !== false && (
                    <p className="text-[10px] text-gray-400 mt-0.5">{hikeTime}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
