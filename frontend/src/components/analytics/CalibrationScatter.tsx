"use client";

import { useMemo } from "react";
import {
    ScatterChart, Scatter, XAxis, YAxis, ZAxis,
    Tooltip, ResponsiveContainer, Legend, ReferenceLine, CartesianGrid,
} from "recharts";
import type { CalibrationPoint } from "@/lib/galileoTypes";
import { TOOLTIP_STYLE } from "@/lib/chartConfig";

const PALETTE = [
    "#22d3ee", "#fb7185", "#14b8a6", "#4ade80", "#fbbf24",
    "#60a5fa", "#f472b6", "#2dd4bf", "#fb923c", "#f59e0b",
];

interface CalibrationScatterProps {
    points: CalibrationPoint[];
    modelNames: Map<string, string>;
}

export default function CalibrationScatter({ points, modelNames }: CalibrationScatterProps) {
    const grouped = useMemo(() => {
        const map = new Map<string, { x: number; y: number }[]>();
        for (const p of points) {
            const arr = map.get(p.llm_id) ?? [];
            arr.push({ x: p.score_total, y: p.calibration });
            map.set(p.llm_id, arr);
        }
        return map;
    }, [points]);

    if (!points.length) {
        return (
            <div className="flex items-center justify-center h-64 text-gray-500">
                No calibration data available
            </div>
        );
    }

    const ids = Array.from(grouped.keys());

    return (
        <ResponsiveContainer width="100%" height={360}>
            <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 6" stroke="#1e293b" />
                <XAxis
                    type="number"
                    dataKey="x"
                    name="Score"
                    domain={[0, 100]}
                    stroke="#334155"
                    fontSize={11}
                    tickLine={false}
                    label={{ value: "Score", position: "bottom", fill: "#64748b", fontSize: 10 }}
                />
                <YAxis
                    type="number"
                    dataKey="y"
                    name="Calibration"
                    domain={[0, 1]}
                    stroke="#334155"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    label={{ value: "Calibration", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 10 }}
                />
                <ZAxis range={[40, 40]} />
                <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    formatter={(v: number, name: string) => {
                        if (name === "Score") return [v.toFixed(1), "Score"];
                        return [v.toFixed(2), "Calibration"];
                    }}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                <ReferenceLine
                    segment={[{ x: 0, y: 0 }, { x: 100, y: 1 }]}
                    stroke="#334155"
                    strokeDasharray="6 4"
                    strokeWidth={1.5}
                    label={{ value: "Perfect", fill: "#475569", fontSize: 10 }}
                />
                {ids.map((id, i) => (
                    <Scatter
                        key={id}
                        name={modelNames.get(id) ?? id.slice(0, 8)}
                        data={grouped.get(id)}
                        fill={PALETTE[i % PALETTE.length]}
                        opacity={0.8}
                        style={{ filter: `drop-shadow(0 0 4px ${PALETTE[i % PALETTE.length]}60)` }}
                    />
                ))}
            </ScatterChart>
        </ResponsiveContainer>
    );
}
