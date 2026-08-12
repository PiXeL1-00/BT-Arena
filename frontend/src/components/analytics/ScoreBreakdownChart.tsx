"use client";

import { useMemo } from "react";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
    CartesianGrid,
} from "recharts";
import type { ScoreBreakdownItem } from "@/lib/galileoTypes";
import { TOOLTIP_STYLE } from "@/lib/chartConfig";

const DIMENSION_COLORS: Record<string, string> = {
    correctness: "#412AD1",
    grounding: "#29BC41",
    calibration: "#FCC503",
    falsifiable: "#B50BBB",
    deference_penalty: "#0C0809",
    refusal_penalty: "#292524",
};

const DIMENSION_LABELS: Record<string, string> = {
    correctness: "Correctness",
    grounding: "Grounding",
    calibration: "Calibration",
    falsifiable: "Falsifiable",
    deference_penalty: "Deference Pen.",
    refusal_penalty: "Refusal Pen.",
};

interface ScoreBreakdownChartProps {
    items: ScoreBreakdownItem[];
    modelNames: Map<string, string>;
}

export default function ScoreBreakdownChart({ items, modelNames }: ScoreBreakdownChartProps) {
    const chartData = useMemo(() =>
        items.map((d) => ({
            name: (modelNames.get(d.llm_id) ?? d.llm_id.slice(0, 8)).split("/").pop()!,
            correctness: Math.round(d.correctness * 100) / 100,
            grounding: Math.round(d.grounding * 100) / 100,
            calibration: Math.round(d.calibration * 100) / 100,
            falsifiable: Math.round(d.falsifiable * 100) / 100,
            deference_penalty: Math.round(Math.abs(d.deference_penalty) * 100) / 100,
            refusal_penalty: Math.round(Math.abs(d.refusal_penalty) * 100) / 100,
        })),
        [items, modelNames]);

    if (!chartData.length) {
        return (
            <div className="flex items-center justify-center h-64 text-[#292524]/60">
                No breakdown data available
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 15, left: -10 }}>
                <defs>
                    {Object.entries(DIMENSION_COLORS).map(([key, color]) => (
                        <linearGradient key={key} id={`bd-${key}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={color} stopOpacity={0.9} />
                            <stop offset="100%" stopColor={color} stopOpacity={0.45} />
                        </linearGradient>
                    ))}
                </defs>
                <CartesianGrid strokeDasharray="3 6" stroke="rgba(41, 37, 36, 0.15)" vertical={false} />
                <XAxis dataKey="name" stroke="#292524" fontSize={11} angle={-10} textAnchor="end" tickLine={false} />
                <YAxis stroke="#292524" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    cursor={{ fill: "rgba(65, 42, 209, 0.05)" }}
                />
                <Legend
                    wrapperStyle={{ fontSize: "9px", paddingTop: "4px", lineHeight: "14px" }}
                    iconSize={8}
                />
                {Object.entries(DIMENSION_COLORS).map(([key]) => (
                    <Bar
                        key={key}
                        dataKey={key}
                        name={DIMENSION_LABELS[key]}
                        stackId="score"
                        fill={`url(#bd-${key})`}
                    />
                ))}
            </BarChart>
        </ResponsiveContainer>
    );
}
