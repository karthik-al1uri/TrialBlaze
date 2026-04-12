"use client";

import type { MapTrail } from "@/lib/api";

interface ClusterDrawerProps {
  trails: MapTrail[];
  onTrailSelect: (trail: MapTrail) => void;
  onClose: () => void;
  isOpen: boolean;
}

export default function ClusterDrawer({
  trails,
  onTrailSelect,
  onClose,
  isOpen,
}: ClusterDrawerProps) {
  return (
    <div
      className={`
        fixed bottom-0 left-0 right-0 z-[9998]
        bg-gray-900 border-t border-gray-700
        rounded-t-2xl shadow-2xl
        transform transition-transform duration-300 ease-out
        ${isOpen ? "translate-y-0" : "translate-y-full"}
        max-h-72 overflow-y-auto
      `}
    >
      {/* Drag handle */}
      <div className="flex justify-center pt-3 pb-2">
        <div className="w-10 h-1 bg-gray-600 rounded-full" />
      </div>

      {/* Header */}
      <div className="flex items-center justify-between px-4 pb-3">
        <p className="text-sm font-semibold text-white">
          {trails.length} trails in this area
        </p>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white text-lg leading-none"
        >
          ×
        </button>
      </div>

      {/* Trail mini cards */}
      <div className="px-4 pb-4 space-y-2">
        {trails.map((trail, i) => {
          const diffColor =
            (trail.difficulty || "").toLowerCase() === "easy"
              ? "text-green-400"
              : (trail.difficulty || "").toLowerCase() === "hard"
                ? "text-red-400"
                : "text-amber-400";
          return (
            <button
              key={`${trail.name}-${i}`}
              onClick={() => {
                onTrailSelect(trail);
                onClose();
              }}
              className="w-full text-left bg-gray-800 hover:bg-gray-700
                rounded-xl px-4 py-3 transition-colors border
                border-gray-700 hover:border-gray-500"
            >
              <div className="flex items-center justify-between">
                <p className="text-white text-sm font-medium truncate max-w-[60%]">
                  {trail.name}
                </p>
                <span className={`text-xs font-semibold ${diffColor}`}>
                  {trail.difficulty
                    ? trail.difficulty.charAt(0).toUpperCase() +
                      trail.difficulty.slice(1)
                    : "Unknown"}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-gray-400 text-xs">
                  {trail.length_miles
                    ? `${trail.length_miles.toFixed(1)} mi`
                    : "Distance N/A"}
                </span>
                {trail.nearby_city && (
                  <span className="text-gray-500 text-xs truncate">
                    {trail.nearby_city}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
