"use client";

import { useMemo } from "react";
import {
    LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
    CartesianGrid, Legend,
} from "recharts";
import type { ModelTrendSeries } from "@/lib/galileoTypes";
import { TOOLTIP_STYLE } from "@/lib/chartConfig";

const PALETTE = [
    "#22d3ee", "#fb7185", "#14b8a6", "#4ade80", "#fbbf24",
    "#60a5fa", "#f472b6", "#2dd4bf", "#fb923c", "#f59e0b",
];

interface TrendChartProps {
    series: ModelTrendSeries[];
    modelNames: Map<string, string>;
}

export default function TrendChart({ series, modelNames }: TrendChartProps) {
    const chartData = useMemo(() => {
        const bucketMap = new Map<string, Record<string, number | string>>();

        for (const s of series) {
            for (const b of s.buckets) {
                const key = b.bucket.slice(0, 10);
                const existing = bucketMap.get(key) ?? { date: key };
                if (b.score_avg !== null) {
                    existing[s.llm_id] = Math.round(b.score_avg * 100) / 100;
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
                No trend data available
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
                <CartesianGrid strokeDasharray="3 6" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#334155" fontSize={10} tickLine={false} />
                <YAxis stroke="#334155" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend
                    wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                    iconType="plainline"
                />
                {series.map((s, i) => (
                    <Line
                        key={s.llm_id}
                        type="monotone"
                        dataKey={s.llm_id}
                        name={(modelNames.get(s.llm_id) ?? s.llm_id).split("/").pop()!}
                        stroke={PALETTE[i % PALETTE.length]}
                        strokeWidth={2.5}
                        dot={{ r: 3, fill: PALETTE[i % PALETTE.length], strokeWidth: 0 }}
                        activeDot={{
                            r: 5,
                            strokeWidth: 2,
                            stroke: PALETTE[i % PALETTE.length],
                            fill: "#0f172a",
                            style: { filter: `drop-shadow(0 0 6px ${PALETTE[i % PALETTE.length]})` },
                        }}
                        connectNulls={true}
                    />
                ))}
            </LineChart>
        </ResponsiveContainer>
    );
}
