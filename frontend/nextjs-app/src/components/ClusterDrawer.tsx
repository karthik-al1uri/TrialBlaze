"use client";

interface Trail {
  name: string;
  difficulty?: string;
  length_miles?: number;
}

interface ClusterDrawerProps {
  trails: Trail[];
  onTrailSelect: (trail: Trail) => void;
  onClose: () => void;
  isOpen: boolean;
}

export default function ClusterDrawer({ trails, onTrailSelect, onClose, isOpen }: ClusterDrawerProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t rounded-t-2xl shadow-xl max-h-64 overflow-y-auto">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <p className="font-semibold text-sm">{trails.length} trails in this area</p>
        <button onClick={onClose} className="text-gray-500 text-xl leading-none">&times;</button>
      </div>
      <div className="p-3 space-y-2">
        {trails.map((trail) => (
          <button
            key={trail.name}
            onClick={() => { onTrailSelect(trail); onClose(); }}
            className="w-full text-left px-3 py-2 rounded-lg border hover:bg-gray-50 transition-colors"
          >
            <p className="text-sm font-medium">{trail.name}</p>
            <p className="text-xs text-gray-500">
              {trail.difficulty} · {trail.length_miles ? `${trail.length_miles} mi` : "N/A"}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
