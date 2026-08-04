"use client";

import { useMemo } from "react";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    CartesianGrid, Cell,
} from "recharts";
import type { CostPerPassItem } from "@/lib/galileoTypes";
import { TOOLTIP_STYLE } from "@/lib/chartConfig";

const BAR_COLORS = [
    "#fb7185", "#f472b6", "#14b8a6", "#f59e0b", "#60a5fa",
    "#22d3ee", "#2dd4bf", "#4ade80", "#fbbf24", "#fb923c",
];

interface CostPerPassChartProps {
    items: CostPerPassItem[];
    modelNames: Map<string, string>;
}

export default function CostPerPassChart({ items, modelNames }: CostPerPassChartProps) {
    const chartData = useMemo(() =>
        items
            .filter((d) => d.cost_per_pass !== null)
            .map((d) => ({
                name: (modelNames.get(d.llm_id) ?? d.llm_id.slice(0, 8)).split("/").pop()!,
                cost: Math.round((d.cost_per_pass ?? 0) * 10000) / 10000,
                passes: d.passing_runs,
                total: d.total_runs,
            }))
            .sort((a, b) => b.cost - a.cost),
        [items, modelNames]);

    if (!chartData.length) {
        return (
            <div className="flex items-center justify-center h-64 text-gray-500">
                No cost data available
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 15, left: 0 }}>
                <defs>
                    {chartData.map((_, i) => (
                        <linearGradient key={i} id={`cost-bar-${i}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={BAR_COLORS[i % BAR_COLORS.length]} stopOpacity={0.9} />
                            <stop offset="100%" stopColor={BAR_COLORS[i % BAR_COLORS.length]} stopOpacity={0.3} />
                        </linearGradient>
                    ))}
                </defs>
                <CartesianGrid strokeDasharray="3 6" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="name" stroke="#334155" fontSize={11} angle={-10} textAnchor="end" tickLine={false} />
                <YAxis
                    stroke="#334155"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v: number) => `$${v}`}
                />
                <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    formatter={(v: number, name: string) => {
                        if (name === "cost") return [`$${v.toFixed(4)}`, "Cost / Pass"];
                        return [v, name];
                    }}
                    cursor={{ fill: "rgba(251, 113, 133, 0.05)" }}
                />
                <Bar dataKey="cost" radius={[6, 6, 0, 0]}>
                    {chartData.map((_, i) => (
                        <Cell key={i} fill={`url(#cost-bar-${i})`} />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}
