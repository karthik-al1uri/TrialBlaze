"use client";

import { useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";
import { fetchGpxData, type GpxElevationPoint } from "@/lib/api";

interface ElevationChartProps {
  trailName: string;
}

export default function ElevationChart({ trailName }: ElevationChartProps) {
  const [profile, setProfile] = useState<GpxElevationPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<{ gain: number; min: number; max: number } | null>(null);

  useEffect(() => {
    setLoading(true);
    setProfile([]);
    setStats(null);
    fetchGpxData(trailName).then((data) => {
      if (data && data.elevation_profile?.length > 1) {
        setProfile(data.elevation_profile);
        setStats({
          gain: data.stats.elevation_gain_ft,
          min: data.stats.min_elevation_ft ?? 0,
          max: data.stats.max_elevation_ft ?? 0,
        });
      }
      setLoading(false);
    });
  }, [trailName]);

  if (loading) {
    return (
      <div className="h-20 flex items-center justify-center">
        <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!profile.length) return null;

  const W = 320;
  const H = 80;
  const PAD = { top: 8, bottom: 20, left: 36, right: 8 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const elevs = profile.map((p) => p.elev_ft);
  const dists = profile.map((p) => p.distance_mi);
  const minE = Math.min(...elevs);
  const maxE = Math.max(...elevs);
  const maxD = Math.max(...dists);
  const rangeE = maxE - minE || 1;

  const toX = (d: number) => PAD.left + (d / maxD) * chartW;
  const toY = (e: number) => PAD.top + chartH - ((e - minE) / rangeE) * chartH;

  const pathD = profile
    .map((p, i) => `${i === 0 ? "M" : "L"}${toX(p.distance_mi).toFixed(1)},${toY(p.elev_ft).toFixed(1)}`)
    .join(" ");

  const fillD =
    pathD +
    ` L${toX(maxD).toFixed(1)},${(PAD.top + chartH).toFixed(1)} L${PAD.left},${(PAD.top + chartH).toFixed(1)} Z`;

  const yLabels = [minE, minE + rangeE / 2, maxE];

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1">
          <TrendingUp className="w-3 h-3" /> Elevation Profile
        </span>
        {stats && (
          <span className="text-[10px] text-gray-400">
            +{Math.round(stats.gain)} ft gain · {Math.round(stats.min).toLocaleString()}–{Math.round(stats.max).toLocaleString()} ft
          </span>
        )}
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="overflow-visible">
        {/* Grid lines */}
        {yLabels.map((e, i) => (
          <g key={i}>
            <line
              x1={PAD.left}
              y1={toY(e)}
              x2={PAD.left + chartW}
              y2={toY(e)}
              stroke="#e5e7eb"
              strokeWidth="0.5"
              strokeDasharray="3,3"
            />
            <text
              x={PAD.left - 3}
              y={toY(e) + 3}
              textAnchor="end"
              fontSize="7"
              fill="#9ca3af"
            >
              {Math.round(e / 100) * 100}
            </text>
          </g>
        ))}
        {/* X axis */}
        <line
          x1={PAD.left}
          y1={PAD.top + chartH}
          x2={PAD.left + chartW}
          y2={PAD.top + chartH}
          stroke="#d1d5db"
          strokeWidth="0.5"
        />
        {/* X labels */}
        {[0, maxD / 2, maxD].map((d, i) => (
          <text
            key={i}
            x={toX(d)}
            y={H - 4}
            textAnchor={i === 0 ? "start" : i === 2 ? "end" : "middle"}
            fontSize="7"
            fill="#9ca3af"
          >
            {d.toFixed(1)} mi
          </text>
        ))}
        {/* Filled area */}
        <path d={fillD} fill="#10b98120" />
        {/* Line */}
        <path d={pathD} fill="none" stroke="#10b981" strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
    </div>
  );
}
