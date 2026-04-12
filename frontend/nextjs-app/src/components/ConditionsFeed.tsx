"use client";

import { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { fetchRecentConditions, type RecentCondition } from "@/lib/api";

const CONDITION_STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  Clear:        { bg: "bg-green-50",  text: "text-green-700",  dot: "bg-green-500" },
  Muddy:        { bg: "bg-amber-50",  text: "text-amber-700",  dot: "bg-amber-400" },
  Snow:         { bg: "bg-blue-50",   text: "text-blue-700",   dot: "bg-blue-400"  },
  Icy:          { bg: "bg-cyan-50",   text: "text-cyan-700",   dot: "bg-cyan-400"  },
  "Downed Tree":{ bg: "bg-orange-50", text: "text-orange-700", dot: "bg-orange-400"},
  "Washed Out": { bg: "bg-red-50",    text: "text-red-700",    dot: "bg-red-500"   },
};

function timeAgo(isoString: string): string {
  try {
    const diff = Date.now() - new Date(isoString).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  } catch {
    return "";
  }
}

interface ConditionsFeedProps {
  onTrailClick?: (name: string) => void;
}

export default function ConditionsFeed({ onTrailClick }: ConditionsFeedProps) {
  const [conditions, setConditions] = useState<RecentCondition[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentConditions(12).then((data) => {
      setConditions(data);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="px-4 py-3 flex items-center gap-2 text-xs text-gray-400">
        <div className="w-3 h-3 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
        Loading conditions…
      </div>
    );
  }

  if (!conditions.length) {
    return (
      <div className="px-4 py-3 text-xs text-gray-400 italic">
        No trail conditions reported yet.
      </div>
    );
  }

  return (
    <div className="px-3 py-2 space-y-1.5">
      <div className="flex items-center gap-1.5 mb-2">
        <Activity className="w-3.5 h-3.5 text-emerald-600" />
        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Live Trail Conditions</span>
      </div>
      {conditions.map((c, i) => {
        const style = CONDITION_STYLES[c.condition] ?? { bg: "bg-gray-50", text: "text-gray-600", dot: "bg-gray-400" };
        return (
          <div key={i} className="flex items-start gap-2 rounded-lg bg-gray-50 px-2.5 py-2 border border-gray-100">
            <span className={`w-2 h-2 rounded-full mt-1 shrink-0 ${style.dot}`} />
            <div className="flex-1 min-w-0">
              <button
                onClick={() => onTrailClick?.(c.trail_name)}
                className="text-[11px] font-semibold text-gray-700 hover:text-emerald-700 transition-colors truncate block w-full text-left"
              >
                {c.trail_name}
              </button>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${style.bg} ${style.text}`}>
                  {c.condition}
                </span>
                {c.note && (
                  <span className="text-[10px] text-gray-400 truncate">{c.note}</span>
                )}
              </div>
            </div>
            <span className="text-[9px] text-gray-300 shrink-0 mt-0.5">{timeAgo(c.reported_at)}</span>
          </div>
        );
      })}
    </div>
  );
}
