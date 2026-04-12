"use client";

import { useState } from "react";
import { X, Loader2, CalendarDays, Sparkles, Copy, Check } from "lucide-react";
import { generateItinerary } from "@/lib/api";

interface ItineraryBuilderProps {
  onClose: () => void;
  defaultRegion?: string;
}

const REGIONS = ["Rocky Mountains", "Boulder", "Denver Foothills", "Colorado Springs", "Aspen", "Telluride", "Steamboat Springs"];

export default function ItineraryBuilder({ onClose, defaultRegion }: ItineraryBuilderProps) {
  const [days, setDays] = useState(3);
  const [difficulty, setDifficulty] = useState("");
  const [region, setRegion] = useState(defaultRegion || "");
  const [interests, setInterests] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    setResult(null);
    const data = await generateItinerary(
      days,
      difficulty || undefined,
      region || undefined,
      interests || undefined
    );
    setResult(data.itinerary);
    setLoading(false);
  };

  const handleCopy = () => {
    if (result) {
      navigator.clipboard.writeText(result).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  return (
    <div className="fixed inset-0 z-[9995] flex items-end md:items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-full md:max-w-lg bg-white md:rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-emerald-700 to-emerald-600 shrink-0">
          <span className="text-sm font-semibold text-white flex items-center gap-2">
            <CalendarDays className="w-4 h-4" /> Plan My Hike
          </span>
          <button onClick={onClose} className="p-1 rounded hover:bg-white/20 text-white transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!result ? (
            <>
              {/* Days */}
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Trip Length</label>
                <div className="flex gap-2 mt-2">
                  {[1, 2, 3, 5, 7].map((d) => (
                    <button
                      key={d}
                      onClick={() => setDays(d)}
                      className={`flex-1 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                        days === d ? "bg-emerald-600 text-white border-emerald-600" : "bg-gray-50 text-gray-600 border-gray-200 hover:border-emerald-400"
                      }`}
                    >
                      {d}d
                    </button>
                  ))}
                </div>
              </div>

              {/* Region */}
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Region (optional)</label>
                <select
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full mt-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">Any region in Colorado</option>
                  {REGIONS.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>

              {/* Difficulty */}
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Difficulty (optional)</label>
                <div className="flex gap-2 mt-1.5">
                  {[["", "Any"], ["easy", "Easy"], ["moderate", "Moderate"], ["hard", "Hard"]].map(([val, label]) => (
                    <button
                      key={val}
                      onClick={() => setDifficulty(val)}
                      className={`flex-1 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                        difficulty === val ? "bg-emerald-600 text-white border-emerald-600" : "bg-gray-50 text-gray-600 border-gray-200 hover:border-emerald-400"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Interests */}
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Interests (optional)</label>
                <input
                  type="text"
                  value={interests}
                  onChange={(e) => setInterests(e.target.value)}
                  placeholder="e.g. waterfalls, wildlife, summit views"
                  className="w-full mt-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <button
                onClick={handleGenerate}
                disabled={loading}
                className="w-full py-2.5 bg-gradient-to-r from-emerald-600 to-emerald-500 text-white text-sm font-semibold rounded-xl hover:from-emerald-700 hover:to-emerald-600 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
              >
                {loading ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Generating your itinerary…</>
                ) : (
                  <><Sparkles className="w-4 h-4" /> Generate Itinerary</>
                )}
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-700">Your {days}-Day Colorado Hike Plan</span>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-gray-100 hover:bg-gray-200 text-xs text-gray-600 transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
              <div className="bg-gray-50 rounded-xl p-4 text-sm text-gray-700 leading-relaxed whitespace-pre-wrap border border-gray-200">
                {result}
              </div>
              <button
                onClick={() => setResult(null)}
                className="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-xl transition-colors"
              >
                ← Adjust preferences
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
