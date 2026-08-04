"use client";

import { useMemo } from "react";
import {
    AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
    Legend, CartesianGrid,
} from "recharts";
import type { HallucinationTrendSeries } from "@/lib/galileoTypes";
import { TOOLTIP_STYLE } from "@/lib/chartConfig";

const PALETTE = [
    "#22d3ee", "#fb7185", "#14b8a6", "#4ade80", "#fbbf24",
    "#60a5fa", "#f472b6", "#2dd4bf", "#fb923c", "#f59e0b",
];

interface HallucinationTrendChartProps {
    series: HallucinationTrendSeries[];
    modelNames: Map<string, string>;
}

export default function HallucinationTrendChart({ series, modelNames }: HallucinationTrendChartProps) {
    const chartData = useMemo(() => {
        const bucketMap = new Map<string, Record<string, number | string>>();

        for (const s of series) {
            for (const b of s.buckets) {
                const key = String(b.bucket).slice(0, 10);
                const existing = bucketMap.get(key) ?? { date: key };
                if (b.hallucination_rate !== null) {
                    existing[s.llm_id] = Math.round(b.hallucination_rate * 10000) / 100;
                }
                bucketMap.set(key, existing);
            }
        }

        return Array.from(bucketMap.values()).sort(
            (a, b) => String(a.date).localeCompare(String(b.date)),
        );
    }, [series]);

    if (!chartData.length) {
        return (
            <div className="flex items-center justify-center h-64 text-gray-500">
                No hallucination data available
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <defs>
                    {series.map((s, i) => (
                        <linearGradient key={s.llm_id} id={`hall-grad-${i}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={PALETTE[i % PALETTE.length]} stopOpacity={0.3} />
                            <stop offset="95%" stopColor={PALETTE[i % PALETTE.length]} stopOpacity={0} />
                        </linearGradient>
                    ))}
                </defs>
                <CartesianGrid strokeDasharray="3 6" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#334155" fontSize={11} tickLine={false} />
                <YAxis
                    stroke="#334155"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v: number) => `${v}%`}
                />
                <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    formatter={(v: number) => [`${v}%`, "Hallucination Rate"]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                {series.map((s, i) => (
                    <Area
                        key={s.llm_id}
                        type="monotone"
                        dataKey={s.llm_id}
                        name={modelNames.get(s.llm_id) ?? s.llm_id.slice(0, 8)}
                        stroke={PALETTE[i % PALETTE.length]}
                        strokeWidth={2.5}
                        fill={`url(#hall-grad-${i})`}
                        dot={false}
                        activeDot={{
                            r: 5,
                            strokeWidth: 2,
                            stroke: PALETTE[i % PALETTE.length],
                            fill: "#0f172a",
                            style: { filter: `drop-shadow(0 0 6px ${PALETTE[i % PALETTE.length]})` },
                        }}
                        connectNulls={false}
                    />
                ))}
            </AreaChart>
        </ResponsiveContainer>
    );
}
