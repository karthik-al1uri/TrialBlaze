"use client";

interface ElevationPoint {
  distance_mi: number;
  elev_ft: number;
}

interface ElevationProfileProps {
  data: ElevationPoint[];
  trailName: string;
}

export default function ElevationProfile({ data }: ElevationProfileProps) {
  if (!data || data.length < 2) return null;

  const elevs = data.map((d) => d.elev_ft);
  const minE = Math.min(...elevs);
  const maxE = Math.max(...elevs);
  const maxDist = data[data.length - 1].distance_mi || 1;
  const gain = Math.round(maxE - minE);

  const W = 280, H = 80, padL = 10, padR = 10, padT = 8, padB = 10;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const toX = (d: number) => padL + (d / maxDist) * plotW;
  const toY = (e: number) => padT + plotH - ((e - minE) / (maxE - minE || 1)) * plotH;

  const pts = data.map((p) => `${toX(p.distance_mi).toFixed(1)},${toY(p.elev_ft).toFixed(1)}`).join("L");
  const pathD = `M${pts}`;
  const areaD = `${pathD}L${toX(maxDist)},${padT + plotH}L${padL},${padT + plotH}Z`;

  return (
    <div className="px-4 py-2">
      <p className="text-xs text-gray-500 mb-1">Elevation Profile · +{gain.toLocaleString()} ft gain</p>
      <svg viewBox="0 0 280 80" className="w-full">
        <path d={areaD} fill="#22c55e" fillOpacity={0.2} />
        <path d={pathD} fill="none" stroke="#22c55e" strokeWidth="1.5" />
      </svg>
    </div>
  );
}
