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
    <div className="glass-panel rounded-3xl p-6 shadow-lg">
      <h2 className="text-lg font-bold text-[#412AD1] mb-4">Model Score Heatmap</h2>
      <div className="space-y-3">
        {Object.entries(byModel).map(([model, scores]) => {
          const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
          const pct = Math.round(avg);
          return (
            <div key={model} className="flex items-center gap-3">
              <span className="text-xs font-mono w-40 truncate text-[#292524]">
                {model}
              </span>
              <div className="flex-1 bg-[#292524]/10 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    pct >= 80
                      ? "bg-[#29BC41]"
                      : pct >= 50
                      ? "bg-[#FCC503]"
                      : "bg-[#B50BBB]"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs text-[#292524] font-mono font-semibold w-10 text-right">{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
