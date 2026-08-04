"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { CaseResult } from "@/lib/types";

interface Props {
  results: CaseResult[];
}

export function PressureScatter({ results }: Props) {
  // For this chart we need pressure_score; approximate from case_id position
  const data = results.map((r, i) => ({
    x: ((i % 10) + 1) * 1, // placeholder pressure
    y: r.score,
    passed: r.passed,
    model: r.model_key,
    caseId: r.case_id,
  }));

  const passData = data.filter((d) => d.passed);
  const failData = data.filter((d) => !d.passed);

  if (data.length === 0) return null;

  return (
    <div className="glass-panel rounded-3xl p-6">
      <h2 className="text-lg font-medium text-cyan-300 mb-4">Score Distribution</h2>
      <ResponsiveContainer width="100%" height={250}>
        <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis
            dataKey="x"
            name="Case #"
            tick={{ fontSize: 11, fill: "rgba(255,255,255,0.6)" }}
          />
          <YAxis
            dataKey="y"
            name="Score"
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: "rgba(255,255,255,0.6)" }}
          />
          <Tooltip
            contentStyle={{
              background: "rgba(255, 255, 255, 0.1)",
              backdropFilter: "blur(16px)",
              border: "1px solid rgba(255, 255, 255, 0.2)",
              borderRadius: "12px",
              color: "#fff",
            }}
          />
          <Legend />
          <Scatter name="Pass" data={passData} fill="#34d399" />
          <Scatter name="Fail" data={failData} fill="#f87171" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
