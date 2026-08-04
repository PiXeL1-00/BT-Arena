"use client";

import type { CaseResult } from "@/lib/types";

interface Props {
  results: CaseResult[];
}

export function TopicHeatmap({ results }: Props) {
  // Group by model_key, compute avg score per model
  const byModel: Record<string, number[]> = {};
  for (const r of results) {
    if (!byModel[r.model_key]) byModel[r.model_key] = [];
    byModel[r.model_key].push(r.score);
  }

  if (Object.keys(byModel).length === 0) return null;

  return (
    <div className="glass-panel rounded-3xl p-6">
      <h2 className="text-lg font-medium text-cyan-300 mb-4">Model Score Heatmap</h2>
      <div className="space-y-3">
        {Object.entries(byModel).map(([model, scores]) => {
          const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
          const pct = Math.round(avg);
          return (
            <div key={model} className="flex items-center gap-3">
              <span className="text-xs font-mono w-40 truncate text-white/60">
                {model}
              </span>
              <div className="flex-1 bg-white/10 rounded-full h-4 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    pct >= 80
                      ? "bg-gradient-to-r from-green-400 to-emerald-500"
                      : pct >= 50
                      ? "bg-gradient-to-r from-yellow-400 to-orange-500"
                      : "bg-gradient-to-r from-red-400 to-pink-500"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs text-white/60 w-10 text-right">{pct}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
