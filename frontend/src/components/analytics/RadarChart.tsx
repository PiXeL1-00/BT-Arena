"use client";

import { useMemo } from "react";
import {
    Radar, RadarChart as RechartsRadarChart, PolarGrid,
    PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip,
} from "recharts";
import type { RadarEntry } from "@/lib/galileoTypes";
import { TOOLTIP_STYLE } from "@/lib/chartConfig";

const PALETTE = [
    "#412AD1", "#B50BBB", "#29BC41", "#FCC503", "#0C0809", "#292524",
];

const DIMENSION_LABELS: Record<string, string> = {
    correctness: "Correctness",
    grounding: "Grounding",
    calibration: "Calibration",
    falsifiable: "Falsifiable",
    deference_penalty: "Deference",
    refusal_penalty: "Refusal",
};

interface RadarChartProps {
    entries: RadarEntry[];
    modelNames: Map<string, string>;
}

export default function RadarChart({ entries, modelNames }: RadarChartProps) {
    const { chartData, llmIds } = useMemo(() => {
        const byDimension = new Map<string, Record<string, number | string>>();
        const ids = new Set<string>();

        for (const e of entries) {
            ids.add(e.llm_id);
            const existing = byDimension.get(e.dimension) ?? {
                dimension: DIMENSION_LABELS[e.dimension] ?? e.dimension,
            };
            if (e.avg_value !== null) {
                existing[e.avg_value !== null ? e.dimension : ""] = Math.round(e.avg_value * 100) / 100;
                existing[e.llm_id] = Math.round(e.avg_value * 100) / 100;
            }
            byDimension.set(e.dimension, existing);
        }

        return {
            chartData: Array.from(byDimension.values()),
            llmIds: Array.from(ids),
        };
    }, [entries]);

    if (!chartData.length) {
        return (
            <div className="flex items-center justify-center h-64 text-[#292524]/60">
                No radar data available
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height="100%">
            <RechartsRadarChart cx="50%" cy="50%" outerRadius="65%" data={chartData}>
                <PolarGrid stroke="rgba(41, 37, 36, 0.15)" strokeDasharray="3 3" />
                <PolarAngleAxis
                    dataKey="dimension"
                    stroke="#292524"
                    fontSize={9}
                    tickLine={false}
                />
                <PolarRadiusAxis stroke="rgba(41, 37, 36, 0.15)" fontSize={10} axisLine={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ fontSize: "9px", paddingTop: "4px", lineHeight: "14px", color: "#292524" }} iconSize={8} />
                {llmIds.map((id, i) => (
                    <Radar
                        key={id}
                        name={(modelNames.get(id) ?? id).split("/").pop()!}
                        dataKey={id}
                        stroke={PALETTE[i % PALETTE.length]}
                        strokeWidth={2}
                        fill={PALETTE[i % PALETTE.length]}
                        fillOpacity={0.12}
                        style={{ filter: `drop-shadow(0 0 4px ${PALETTE[i % PALETTE.length]}40)` }}
                    />
                ))}
            </RechartsRadarChart>
        </ResponsiveContainer>
    );
}
