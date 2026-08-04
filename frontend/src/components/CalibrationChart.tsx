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
    <div className="glass-panel rounded-3xl p-6">
      <h2 className="text-lg font-medium text-cyan-300 mb-4">Score Distribution</h2>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={buckets} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis dataKey="range" tick={{ fontSize: 10, fill: "rgba(255,255,255,0.6)" }} />
          <YAxis tick={{ fontSize: 10, fill: "rgba(255,255,255,0.6)" }} />
          <Tooltip
            contentStyle={{
              background: "rgba(255, 255, 255, 0.1)",
              backdropFilter: "blur(16px)",
              border: "1px solid rgba(255, 255, 255, 0.2)",
              borderRadius: "12px",
              color: "#fff",
            }}
          />
          <Bar dataKey="count" fill="#22d3ee" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
