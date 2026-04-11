"use client";

import { useMemo } from "react";

interface ElevationPoint {
  distance_mi: number;
  elev_ft: number;
}

interface ElevationProfileProps {
  data: ElevationPoint[];
  trailName: string;
}

export default function ElevationProfile({ data, trailName }: ElevationProfileProps) {
  if (!data || data.length < 2) return null;

  const { minElev, maxElev, gainFt, pathD, areaD, xTicks, yTicks } = useMemo(() => {
    const elevs = data.map((d) => d.elev_ft);
    const minE = Math.min(...elevs);
    const maxE = Math.max(...elevs);
    const gain = Math.round(maxE - minE);

    const W = 280;
    const H = 80;
    const padL = 45;
    const padR = 10;
    const padT = 8;
    const padB = 20;

    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const maxDist = data[data.length - 1].distance_mi || 1;
    const eRange = maxE - minE || 1;

    const toX = (d: number) => padL + (d / maxDist) * plotW;
    const toY = (e: number) => padT + plotH - ((e - minE) / eRange) * plotH;

    // Build SVG path
    const pts = data.map((p) => `${toX(p.distance_mi).toFixed(1)},${toY(p.elev_ft).toFixed(1)}`);
    const line = `M${pts.join("L")}`;
    const area = `${line}L${toX(maxDist).toFixed(1)},${(padT + plotH).toFixed(1)}L${padL.toFixed(1)},${(padT + plotH).toFixed(1)}Z`;

    // X-axis ticks (distance)
    const xT = [0, maxDist / 2, maxDist].map((d) => ({
      x: toX(d),
      label: `${d.toFixed(1)}mi`,
    }));

    // Y-axis ticks (elevation)
    const mid = (minE + maxE) / 2;
    const yT = [minE, mid, maxE].map((e) => ({
      y: toY(e),
      label: `${Math.round(e).toLocaleString()}`,
    }));

    return { minElev: minE, maxElev: maxE, gainFt: gain, pathD: line, areaD: area, xTicks: xT, yTicks: yT };
  }, [data]);

  return (
    <div className="px-4 py-2">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">
          Elevation Profile
        </p>
        <span className="text-[10px] text-gray-400">
          +{gainFt.toLocaleString()} ft gain
        </span>
      </div>
      <svg
        viewBox="0 0 280 80"
        className="w-full"
        style={{ height: "auto" }}
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="elevGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.35} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0.05} />
          </linearGradient>
        </defs>
        {/* Area fill */}
        <path d={areaD} fill="url(#elevGrad)" />
        {/* Line */}
        <path d={pathD} fill="none" stroke="#22c55e" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
        {/* Data points */}
        {data.map((pt, i) => {
          const W = 280, padL = 45, padR = 10, padT = 8, padB = 20;
          const plotW = W - padL - padR;
          const plotH = 80 - padT - padB;
          const maxDist = data[data.length - 1].distance_mi || 1;
          const eRange = maxElev - minElev || 1;
          const cx = padL + (pt.distance_mi / maxDist) * plotW;
          const cy = padT + plotH - ((pt.elev_ft - minElev) / eRange) * plotH;
          return (
            <circle key={i} cx={cx} cy={cy} r="2" fill="#22c55e" opacity="0.7">
              <title>{`${pt.distance_mi} mi · ${Math.round(pt.elev_ft).toLocaleString()} ft`}</title>
            </circle>
          );
        })}
        {/* X-axis ticks */}
        {xTicks.map((t, i) => (
          <text key={`x${i}`} x={t.x} y={76} textAnchor="middle" fontSize="7" fill="#9ca3af">
            {t.label}
          </text>
        ))}
        {/* Y-axis ticks */}
        {yTicks.map((t, i) => (
          <text key={`y${i}`} x={42} y={t.y + 2.5} textAnchor="end" fontSize="7" fill="#9ca3af">
            {t.label}
          </text>
        ))}
      </svg>
    </div>
  );
}
