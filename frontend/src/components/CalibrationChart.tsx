"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { CaseResult } from "@/lib/types";

interface Props {
  results: CaseResult[];
}

export function CalibrationChart({ results }: Props) {
  // Bucket scores into ranges
  const buckets = [
    { range: "0-20", count: 0 },
    { range: "21-40", count: 0 },
    { range: "41-60", count: 0 },
    { range: "61-80", count: 0 },
    { range: "81-100", count: 0 },
  ];

  for (const r of results) {
    if (r.score <= 20) buckets[0].count++;
    else if (r.score <= 40) buckets[1].count++;
    else if (r.score <= 60) buckets[2].count++;
    else if (r.score <= 80) buckets[3].count++;
    else buckets[4].count++;
  }

  if (results.length === 0) return null;

  return (
    <div className="glass-panel rounded-3xl p-6 shadow-lg">
      <h2 className="text-lg font-bold text-[#412AD1] mb-4">Score Distribution</h2>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={buckets} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(41,37,36,0.1)" />
          <XAxis dataKey="range" tick={{ fontSize: 10, fill: "rgba(41,37,36,0.7)" }} />
          <YAxis tick={{ fontSize: 10, fill: "rgba(41,37,36,0.7)" }} />
          <Tooltip
            contentStyle={{
              background: "#FFFFFF",
              border: "1px solid rgba(41,37,36,0.15)",
              borderRadius: "12px",
              color: "#292524",
              boxShadow: "0 4px 16px rgba(12,10,9,0.08)"
            }}
          />
          <Bar dataKey="count" fill="#412AD1" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
