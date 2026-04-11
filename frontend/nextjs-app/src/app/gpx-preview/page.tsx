"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";

function GPXPreviewContent() {
  const params = useSearchParams();
  const trailName = params.get("trail") || "";
  const [geometry, setGeometry] = useState<{ coordinates: [number, number][] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!trailName) { setLoading(false); return; }
    fetch(`/api/geometry?names=${encodeURIComponent(trailName)}`)
      .then((r) => r.json())
      .then((d) => {
        const trails = d.trails || [];
        setGeometry(trails.length > 0 ? trails[0] : null);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [trailName]);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <button onClick={() => window.close()} className="text-gray-400 hover:text-white text-sm">
            &larr; Back
          </button>
          <button
            onClick={() => window.open(`/api/geometry/gpx?names=${encodeURIComponent(trailName)}`, "_blank")}
            className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-sm font-medium"
          >
            ⬇ Download GPX
          </button>
        </div>

        <h1 className="text-2xl font-bold mb-1">{trailName}</h1>
        <p className="text-gray-400 text-sm mb-6">Route Preview — GPX Format</p>

        {loading && (
          <div className="h-64 bg-gray-900 rounded-xl flex items-center justify-center">
            <p className="text-gray-500">Loading route...</p>
          </div>
        )}

        {!loading && !geometry && (
          <div className="h-64 bg-gray-900 rounded-xl flex items-center justify-center">
            <p className="text-gray-500">No route data available for this trail</p>
          </div>
        )}

        {!loading && geometry && (
          <div className="bg-gray-900 rounded-xl p-4">
            <p className="text-gray-400 text-sm">
              Route loaded — {geometry.coordinates?.length ?? 0} coordinates.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function GPXPreviewPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-gray-400">Loading...</p>
      </div>
    }>
      <GPXPreviewContent />
    </Suspense>
  );
}