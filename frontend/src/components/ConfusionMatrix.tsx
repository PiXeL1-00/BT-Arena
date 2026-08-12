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
    <div className="glass-panel rounded-3xl p-6 shadow-lg">
      <h2 className="text-lg font-bold text-[#412AD1] mb-4">Confusion Matrix</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[#292524]/10">
              <th className="text-left text-[#292524]/60 py-2 px-3">Actual \ Predicted</th>
              {LABELS.map((l) => (
                <th key={l} className="text-center text-[#292524]/70 py-2 px-3 font-semibold">
                  {l.slice(0, 3)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {LABELS.map((actual) => (
              <tr key={actual} className="border-b border-[#292524]/5">
                <td className="text-[#292524] py-2 px-3 font-medium">
                  {actual.slice(0, 3)}
                </td>
                {LABELS.map((predicted) => {
                  const count = matrix[actual][predicted];
                  const isCorrect = actual === predicted;
                  return (
                    <td
                      key={predicted}
                      className={`text-center py-2 px-3 rounded font-mono ${
                        isCorrect && count > 0
                          ? "bg-[#29BC41]/15 text-[#29BC41] border border-[#29BC41]/30 font-bold"
                          : count > 0
                          ? "bg-[#B50BBB]/15 text-[#B50BBB] border border-[#B50BBB]/30 font-bold"
                          : "text-[#292524]/30"
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
