"use client";

import { useMemo } from "react";
import type { HeatmapCell } from "@/lib/galileoTypes";

interface HeatmapChartProps {
    cells: HeatmapCell[];
    modelNames: Map<string, string>;
}

function scoreStyle(score: number | null): { bg: string; text: string; shadow: string } {
    if (score === null) return { bg: "bg-slate-800/60", text: "text-gray-600", shadow: "" };
    if (score >= 70) return {
        bg: "bg-emerald-500/30",
        text: "text-emerald-300",
        shadow: "shadow-[0_0_8px_rgba(52,211,153,0.25)]",
    };
    if (score >= 40) return {
        bg: "bg-amber-500/25",
        text: "text-amber-300",
        shadow: "shadow-[0_0_8px_rgba(251,191,36,0.2)]",
    };
    return {
        bg: "bg-rose-500/25",
        text: "text-rose-300",
        shadow: "shadow-[0_0_8px_rgba(251,113,133,0.2)]",
    };
}

function scoreLabel(score: number | null): string {
    if (score === null) return "—";
    return String(Math.round(score));
}

export default function HeatmapChart({ cells, modelNames }: HeatmapChartProps) {
    const { caseIds, llmIds, grid } = useMemo(() => {
        const cases = new Set<string>();
        const llms = new Set<string>();
        const map = new Map<string, HeatmapCell>();

        for (const c of cells) {
            cases.add(c.case_id);
            llms.add(c.llm_id);
            map.set(`${c.llm_id}::${c.case_id}`, c);
        }

        return {
            caseIds: Array.from(cases),
            llmIds: Array.from(llms),
            grid: map,
        };
    }, [cells]);

    if (!cells.length) {
        return (
            <div className="flex items-center justify-center h-64 text-gray-500">
                No heatmap data — select a dataset
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
                <thead>
                    <tr className="border-b border-cyan-500/10">
                        <th className="px-2 py-2 text-left text-gray-500 font-medium uppercase tracking-wider text-[10px]">Case</th>
                        {llmIds.map((lid) => (
                            <th key={lid} className="px-2 py-2 text-center text-gray-400 font-medium truncate max-w-[100px] text-[10px] uppercase tracking-wider">
                                {(modelNames.get(lid) ?? lid.slice(0, 8)).split("/").pop()}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {caseIds.map((cid) => (
                        <tr key={cid} className="border-t border-white/[0.03] hover:bg-white/[0.03] transition-colors">
                            <td className="px-2 py-1.5 text-gray-400 truncate max-w-[160px]" title={cid}>
                                {cid}
                            </td>
                            {llmIds.map((lid) => {
                                const cell = grid.get(`${lid}::${cid}`);
                                const s = scoreStyle(cell?.avg_score ?? null);
                                return (
                                    <td key={lid} className="px-1 py-1 text-center">
                                        <span className={`inline-block w-9 rounded-md font-mono text-[10px] leading-6 ${s.bg} ${s.text} ${s.shadow} transition-all`}>
                                            {scoreLabel(cell?.avg_score ?? null)}
                                        </span>
                                    </td>
                                );
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
