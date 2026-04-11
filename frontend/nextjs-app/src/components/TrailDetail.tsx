"use client";

import { useEffect, useState } from "react";
import { X, Mountain, MapPin, Ruler, TrendingUp, Clock } from "lucide-react";

interface Trail {
  name: string;
  difficulty?: string;
  length_miles?: number;
  elevation_gain_ft?: number;
  lat?: number;
  lng?: number;
  nearby_city?: string;
  location?: string;
}

interface TrailDetailProps {
  trail: Trail;
  onClose: () => void;
}

function getDiffStyle(d?: string) {
  switch (d) {
    case "easy": return { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500" };
    case "moderate": return { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" };
    case "hard": return { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" };
    default: return { bg: "bg-gray-50", text: "text-gray-600", dot: "bg-gray-400" };
  }
}

export default function TrailDetail({ trail, onClose }: TrailDetailProps) {
  const diff = getDiffStyle(trail.difficulty);

  return (
    <div className="w-[320px] h-full bg-white border-l border-gray-200 flex flex-col shadow-xl">
      {/* Hero */}
      <div className="relative h-40 bg-gradient-to-br from-emerald-600 to-emerald-800 flex items-center justify-center shrink-0">
        <Mountain className="w-12 h-12 text-white/40" />
        <button
          onClick={onClose}
          className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-black/60 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
        <div className="absolute bottom-3 left-4">
          <h2 className="text-white font-bold text-base drop-shadow">{trail.name}</h2>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Location */}
        {(trail.nearby_city || trail.location) && (
          <div className="flex items-center gap-1.5 text-sm text-gray-500">
            <MapPin className="w-4 h-4 text-gray-400" />
            {trail.nearby_city || trail.location}
          </div>
        )}

        {/* Difficulty badge */}
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${diff.bg} ${diff.text}`}>
          <span className={`w-2 h-2 rounded-full ${diff.dot}`} />
          {trail.difficulty ? trail.difficulty.charAt(0).toUpperCase() + trail.difficulty.slice(1) : "Unknown"}
        </span>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3">
          {trail.length_miles && (
            <div className="bg-gray-50 rounded-xl p-3">
              <div className="flex items-center gap-1.5 text-gray-400 text-xs mb-1">
                <Ruler className="w-3.5 h-3.5" /> Distance
              </div>
              <p className="text-sm font-semibold text-gray-800">{trail.length_miles} mi</p>
            </div>
          )}
          {trail.elevation_gain_ft && (
            <div className="bg-gray-50 rounded-xl p-3">
              <div className="flex items-center gap-1.5 text-gray-400 text-xs mb-1">
                <TrendingUp className="w-3.5 h-3.5" /> Elevation Gain
              </div>
              <p className="text-sm font-semibold text-gray-800">{trail.elevation_gain_ft.toLocaleString()} ft</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
