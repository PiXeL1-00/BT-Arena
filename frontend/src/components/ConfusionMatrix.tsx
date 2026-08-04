"use client";

import type { CaseResult } from "@/lib/types";

interface Props {
  results: CaseResult[];
}

const LABELS = ["SUPPORTED", "REFUTED", "INSUFFICIENT"] as const;

export function ConfusionMatrix({ results }: Props) {
  // Build a simple count matrix: verdict (predicted) vs label (actual)
  const matrix: Record<string, Record<string, number>> = {};
  for (const l of LABELS) {
    matrix[l] = {};
    for (const v of LABELS) matrix[l][v] = 0;
  }

  for (const r of results) {
    const actual = r.label || "INSUFFICIENT";
    const predicted = r.verdict || "INSUFFICIENT";
    if (matrix[actual] && matrix[actual][predicted] !== undefined) {
      matrix[actual][predicted]++;
    }
  }

  if (results.length === 0) return null;

  return (
    <div className="glass-panel rounded-3xl p-6">
      <h2 className="text-lg font-medium text-cyan-300 mb-4">Confusion Matrix</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="text-left text-white/50 py-2 px-3">Actual \ Predicted</th>
              {LABELS.map((l) => (
                <th key={l} className="text-center text-white/60 py-2 px-3">
                  {l.slice(0, 3)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {LABELS.map((actual) => (
              <tr key={actual}>
                <td className="text-white/60 py-2 px-3 font-medium">
                  {actual.slice(0, 3)}
                </td>
                {LABELS.map((predicted) => {
                  const count = matrix[actual][predicted];
                  const isCorrect = actual === predicted;
                  return (
                    <td
                      key={predicted}
                      className={`text-center py-2 px-3 rounded ${
                        isCorrect && count > 0
                          ? "bg-green-500/20 text-green-300 border border-green-500/30"
                          : count > 0
                          ? "bg-red-500/20 text-red-300 border border-red-500/30"
                          : "text-white/30"
                      }`}
                    >
                      {count}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
