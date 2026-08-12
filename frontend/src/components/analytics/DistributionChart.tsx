"use client";

import { useMemo } from "react";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    ErrorBar, CartesianGrid, Cell,
} from "recharts";
import type { DistributionItem } from "@/lib/galileoTypes";
import { TOOLTIP_STYLE } from "@/lib/chartConfig";

const BAR_COLORS = [
    "#412AD1", "#B50BBB", "#29BC41", "#FCC503", "#0C0809", "#292524",
];

interface DistributionChartProps {
    items: DistributionItem[];
    modelNames: Map<string, string>;
}

export default function DistributionChart({ items, modelNames }: DistributionChartProps) {
    const chartData = useMemo(() => {
        return items
            .filter((d) => d.mean !== null)
            .map((d) => ({
                name: (modelNames.get(d.llm_id) ?? d.llm_id.slice(0, 8)).split("/").pop()!,
                mean: Math.round((d.mean ?? 0) * 100) / 100,
                p25: d.p25,
                p75: d.p75,
                spread: d.stddev ? Math.round(d.stddev * 100) / 100 : 0,
                n: d.n,
            }))
            .sort((a, b) => b.mean - a.mean);
    }, [items, modelNames]);

    if (!chartData.length) {
        return (
            <div className="flex items-center justify-center h-64 text-[#292524]/60">
                No distribution data available
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 15, left: -10 }}>
                <defs>
                    {chartData.map((_, i) => (
                        <linearGradient key={i} id={`dist-bar-${i}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={BAR_COLORS[i % BAR_COLORS.length]} stopOpacity={0.9} />
                            <stop offset="100%" stopColor={BAR_COLORS[i % BAR_COLORS.length]} stopOpacity={0.3} />
                        </linearGradient>
                    ))}
                </defs>
                <CartesianGrid strokeDasharray="3 6" stroke="rgba(41, 37, 36, 0.15)" vertical={false} />
                <XAxis
                    dataKey="name"
                    stroke="#292524"
                    fontSize={11}
                    angle={-10}
                    textAnchor="end"
                    tickLine={false}
                />
                <YAxis stroke="#292524" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    formatter={(v: number, name: string) => {
                        if (name === "mean") return [`${v}`, "Mean Score"];
                        return [v, name];
                    }}
                    cursor={{ fill: "rgba(65, 42, 209, 0.05)" }}
                />
                <Bar dataKey="mean" radius={[6, 6, 0, 0]}>
                    {chartData.map((_, i) => (
                        <Cell key={`cell-${i}`} fill={`url(#dist-bar-${i})`} />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}
