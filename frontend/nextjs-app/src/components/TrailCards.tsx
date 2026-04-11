"use client";

import { Mountain, MapPin, Ruler } from "lucide-react";

interface Trail {
  name: string;
  difficulty?: string;
  length_miles?: number;
  location?: string;
  nearby_city?: string;
}

interface TrailCardsProps {
  trails: Trail[];
  onTrailClick?: (trail: Trail) => void;
}

export default function TrailCards({ trails, onTrailClick }: TrailCardsProps) {
  if (trails.length === 0) return null;

  return (
    <div className="p-3 space-y-2">
      {trails.map((t, i) => (
        <div
          key={`${t.name}-${i}`}
          onClick={() => onTrailClick?.(t)}
          className="flex gap-3 p-2 border rounded-xl cursor-pointer hover:shadow-md transition-shadow bg-white"
        >
          <div className="w-16 h-16 rounded-lg bg-emerald-600 flex items-center justify-center shrink-0">
            <Mountain className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1 min-w-0 py-0.5">
            <p className="text-sm font-semibold text-gray-800 truncate">{t.name}</p>
            {(t.nearby_city || t.location) && (
              <div className="flex items-center gap-1 mt-0.5">
                <MapPin className="w-3 h-3 text-gray-400" />
                <span className="text-xs text-gray-400 truncate">{t.nearby_city || t.location}</span>
              </div>
            )}
            <div className="flex items-center gap-2 mt-1">
              {t.difficulty && (
                <span className="text-xs font-medium text-gray-600 capitalize">{t.difficulty}</span>
              )}
              {t.length_miles && (
                <span className="flex items-center gap-0.5 text-xs text-gray-500">
                  <Ruler className="w-3 h-3" />
                  {t.length_miles} mi
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
