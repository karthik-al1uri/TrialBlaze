"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import dynamic from "next/dynamic";

const RouteMap = dynamic(() => import("@/components/RouteMap"), {
  ssr: false,
});

interface ElevPoint {
  distance_mi: number;
  elev_ft: number;
}

interface TrailGeometry {
  name: string;
  feature_id: number;
  coordinates: [number, number][];
  elevation_profile: ElevPoint[];
}

function GPXPreviewContent() {
  const params = useSearchParams();
  const trailName = params.get("trail") || "";
  const [geometry, setGeometry] = useState<TrailGeometry | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!trailName) {
      setLoading(false);
      return;
    }
    fetch(`/api/geometry?names=${encodeURIComponent(trailName)}`)
      .then((r) => r.json())
      .then((d) => {
        const trails = d.trails || [];
        setGeometry(trails.length > 0 ? trails[0] : null);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [trailName]);

  const handleDownload = () => {
    window.open(
      `/api/geometry/gpx?names=${encodeURIComponent(trailName)}`,
      "_blank"
    );
  };

  const elevProfile = geometry?.elevation_profile || [];
  const hasElev = elevProfile.length > 0;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => window.close()}
            className="text-gray-400 hover:text-white flex items-center gap-2 text-sm"
          >
            &larr; Back
          </button>
          <button
            onClick={handleDownload}
            className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
          >
            ⬇ Download GPX
          </button>
        </div>

        <h1 className="text-2xl font-bold mb-2">{trailName}</h1>
        <p className="text-gray-400 text-sm mb-6">
          Route Preview &mdash; GPX Format
        </p>

        {loading && (
          <div className="h-96 bg-gray-900 rounded-xl flex items-center justify-center">
            <p className="text-gray-500">Loading route...</p>
          </div>
        )}

        {!loading && !geometry && (
          <div className="h-96 bg-gray-900 rounded-xl flex items-center justify-center">
            <p className="text-gray-500">
              No route data available for this trail
            </p>
          </div>
        )}

        {!loading && geometry && (
          <>
            {/* Route map */}
            <div className="h-96 rounded-xl overflow-hidden mb-6">
              <RouteMap geometry={geometry} trailName={trailName} />
            </div>

            {/* Elevation Stats */}
            {hasElev && (
              <div className="bg-gray-900 rounded-xl p-4 mb-6">
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  Elevation Data
                </h2>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div>
                    <p className="text-xs text-gray-500">Start</p>
                    <p className="text-white font-medium">
                      {elevProfile[0]?.elev_ft?.toLocaleString()} ft
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Peak</p>
                    <p className="text-white font-medium">
                      {Math.max(
                        ...elevProfile.map((p) => p.elev_ft)
                      ).toLocaleString()}{" "}
                      ft
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Gain</p>
                    <p className="text-white font-medium">
                      +
                      {(
                        Math.max(...elevProfile.map((p) => p.elev_ft)) -
                        elevProfile[0]?.elev_ft
                      ).toFixed(0)}{" "}
                      ft
                    </p>
                  </div>
                </div>

                {/* Elevation table */}
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-500 text-xs">
                      <th className="text-left py-1">Mile</th>
                      <th className="text-right py-1">Elevation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {elevProfile.map((p, i) => (
                      <tr key={i} className="border-t border-gray-800">
                        <td className="py-1 text-gray-300">
                          {p.distance_mi?.toFixed(1)} mi
                        </td>
                        <td className="py-1 text-right text-gray-300">
                          {p.elev_ft?.toLocaleString()} ft
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* GPX format explanation */}
            <div className="bg-gray-900 rounded-xl p-4">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
                About GPX Files
              </h2>
              <p className="text-gray-400 text-sm leading-relaxed">
                GPX (GPS Exchange Format) contains the exact trail route with
                GPS coordinates and elevation at every point. Compatible with
                Garmin GPS devices, AllTrails, Strava, Komoot, Gaia GPS, and
                CalTopo.
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function GPXPreviewPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-950 flex items-center justify-center">
          <p className="text-gray-400">Loading...</p>
        </div>
      }
    >
      <GPXPreviewContent />
    </Suspense>
  );
}
