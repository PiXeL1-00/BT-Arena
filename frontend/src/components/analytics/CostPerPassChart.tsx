"use client";

import { useMemo } from "react";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    CartesianGrid, Cell,
} from "recharts";
import type { CostPerPassItem } from "@/lib/galileoTypes";
import { TOOLTIP_STYLE } from "@/lib/chartConfig";

const BAR_COLORS = [
    "#412AD1", "#B50BBB", "#29BC41", "#FCC503", "#0C0809", "#292524",
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
            <div className="flex items-center justify-center h-64 text-[#292524]/60">
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
                <CartesianGrid strokeDasharray="3 6" stroke="rgba(41, 37, 36, 0.15)" vertical={false} />
                <XAxis dataKey="name" stroke="#292524" fontSize={11} angle={-10} textAnchor="end" tickLine={false} />
                <YAxis
                    stroke="#292524"
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
                    cursor={{ fill: "rgba(65, 42, 209, 0.05)" }}
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
