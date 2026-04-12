"use client";

import { X, TrendingUp, Ruler, Star, ChevronDown } from "lucide-react";
import type { MapTrail } from "@/lib/api";

interface TrailComparisonProps {
  trails: MapTrail[];
  onRemove: (name: string) => void;
  onClose: () => void;
}

function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

const DIFF_COLOR: Record<string, string> = {
  easy: "text-green-600 bg-green-50",
  moderate: "text-amber-600 bg-amber-50",
  hard: "text-red-600 bg-red-50",
};

export default function TrailComparison({ trails, onRemove, onClose }: TrailComparisonProps) {
  if (!trails.length) return null;

  const maxDist = Math.max(...trails.map((t) => t.length_miles ?? 0), 1);
  const maxElev = Math.max(...trails.map((t) => t.elevation_gain_ft ?? 0), 1);
  const maxScore = Math.max(...trails.map((t) => t.trailblaze_score ?? 0), 100);

  return (
    <div className="fixed bottom-14 md:bottom-0 left-0 right-0 z-[9990] bg-white border-t border-gray-200 shadow-2xl max-h-72 overflow-y-auto">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100 bg-gray-50">
        <span className="text-xs font-semibold text-gray-700 flex items-center gap-1.5">
          <ChevronDown className="w-3.5 h-3.5" /> Compare Trails ({trails.length})
        </span>
        <button onClick={onClose} className="p-1 rounded hover:bg-gray-200 transition-colors">
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-max text-xs">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-gray-400 uppercase w-24">Metric</th>
              {trails.map((t) => (
                <th key={t.name} className="px-3 py-1.5 text-left min-w-[140px]">
                  <div className="flex items-start justify-between gap-1">
                    <span className="text-gray-800 font-semibold leading-tight line-clamp-2">{t.name}</span>
                    <button
                      onClick={() => onRemove(t.name)}
                      className="shrink-0 p-0.5 rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors mt-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                  {t.difficulty && (
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-medium mt-0.5 ${DIFF_COLOR[t.difficulty.toLowerCase()] ?? "text-gray-600 bg-gray-100"}`}>
                      {t.difficulty}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {/* Distance */}
            <tr>
              <td className="px-3 py-2 text-gray-400 font-medium flex items-center gap-1 whitespace-nowrap">
                <Ruler className="w-3 h-3" /> Distance
              </td>
              {trails.map((t) => (
                <td key={t.name} className="px-3 py-2">
                  <div className="font-semibold text-gray-700 mb-1">
                    {t.length_miles ? `${t.length_miles} mi` : "—"}
                  </div>
                  <Bar value={t.length_miles ?? 0} max={maxDist} color="bg-blue-400" />
                </td>
              ))}
            </tr>
            {/* Elevation */}
            <tr className="bg-gray-50/50">
              <td className="px-3 py-2 text-gray-400 font-medium whitespace-nowrap">
                <div className="flex items-center gap-1"><TrendingUp className="w-3 h-3" /> Elev. Gain</div>
              </td>
              {trails.map((t) => (
                <td key={t.name} className="px-3 py-2">
                  <div className="font-semibold text-gray-700 mb-1">
                    {t.elevation_gain_ft ? `${Math.round(t.elevation_gain_ft).toLocaleString()} ft` : "—"}
                  </div>
                  <Bar value={t.elevation_gain_ft ?? 0} max={maxElev} color="bg-orange-400" />
                </td>
              ))}
            </tr>
            {/* TrailBlaze Score */}
            <tr>
              <td className="px-3 py-2 text-gray-400 font-medium whitespace-nowrap">
                <div className="flex items-center gap-1"><Star className="w-3 h-3" /> TB Score</div>
              </td>
              {trails.map((t) => (
                <td key={t.name} className="px-3 py-2">
                  <div className="font-semibold text-gray-700 mb-1">
                    {t.trailblaze_score ? t.trailblaze_score.toFixed(1) : "—"}
                  </div>
                  <Bar value={t.trailblaze_score ?? 0} max={maxScore} color="bg-emerald-500" />
                </td>
              ))}
            </tr>
            {/* Location */}
            <tr className="bg-gray-50/50">
              <td className="px-3 py-2 text-gray-400 font-medium whitespace-nowrap">Location</td>
              {trails.map((t) => (
                <td key={t.name} className="px-3 py-2 text-gray-600">
                  {t.nearby_city || t.location || "—"}
                </td>
              ))}
            </tr>
            {/* Dogs */}
            <tr>
              <td className="px-3 py-2 text-gray-400 font-medium whitespace-nowrap">Dogs</td>
              {trails.map((t) => (
                <td key={t.name} className="px-3 py-2 text-gray-600 capitalize">
                  {t.dogs || "—"}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
