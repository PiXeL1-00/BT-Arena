"use client";

import type { ModelSummaryItem } from "@/lib/galileoTypes";

interface ModelsTableProps {
    models: ModelSummaryItem[];
    windowDays: number;
}

const RANK_COLORS = [
    "bg-[#FCC503] border-[#FCC503] text-[#0C0A09]",
    "bg-[#292524] border-[#292524] text-[#FFFFFF]",
    "bg-[#B50BBB] border-[#B50BBB] text-[#FFFFFF]",
];

function formatScore(val: number | null): string {
    if (val === null) return "—";
    return val.toFixed(2);
}

function formatDate(iso: string | null): string {
    if (!iso) return "Never";
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function ModelsTable({ models, windowDays }: ModelsTableProps) {
    if (!models.length) {
        return (
            <div className="flex items-center justify-center h-32 text-[#292524]/60">
                No models configured
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-[#292524]/10 text-[#292524]/60 text-[10px] uppercase tracking-[0.15em]">
                        <th className="text-center py-3 px-2 w-10">#</th>
                        <th className="text-left py-3 px-2">Model</th>
                        <th className="text-right py-3 px-2">All‑Time Avg</th>
                        <th className="text-right py-3 px-2">{windowDays}d Avg</th>
                        <th className="text-right py-3 px-2">Runs</th>
                        <th className="text-right py-3 px-2">Last Run</th>
                        <th className="text-center py-3 px-2">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {models.map((m, i) => (
                        <tr
                            key={m.llm_id}
                            className="border-b border-[#292524]/10 hover:bg-[#412AD1]/5 transition-colors group/row"
                        >
                            <td className="text-center py-3 px-2">
                                <span className={`inline-flex items-center justify-center w-6 h-6 rounded-md text-[10px] font-bold border ${i < 3 ? RANK_COLORS[i] : "bg-[#292524]/10 border-[#292524]/20 text-[#292524]/60"}`}>
                                    {i + 1}
                                </span>
                            </td>
                            <td className="py-3 px-2">
                                <span className="font-medium text-[#292524] group-hover/row:text-[#412AD1] transition-colors">{m.display_name}</span>
                                <span className="ml-2 text-[10px] text-[#292524]/50">{m.provider}</span>
                            </td>
                            <td className="text-right py-3 px-2">
                                <span className="font-mono text-[#412AD1] font-semibold">
                                    {formatScore(m.all_time_avg)}
                                </span>
                            </td>
                            <td className="text-right py-3 px-2">
                                <span className="font-mono text-[#29BC41] font-semibold">
                                    {formatScore(m.window_avg)}
                                </span>
                            </td>
                            <td className="text-right py-3 px-2 font-mono text-[#292524]/70 tabular-nums">
                                {m.all_time_runs}
                            </td>
                            <td className="text-right py-3 px-2 text-[#292524]/60 text-xs">
                                {formatDate(m.last_run_at)}
                            </td>
                            <td className="text-center py-3 px-2">
                                {m.is_stale ? (
                                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] rounded-full bg-[#FCC503]/20 text-[#292524] border border-[#FCC503]/40">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#FCC503]" />
                                        Stale
                                    </span>
                                ) : m.all_time_runs === 0 ? (
                                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] rounded-full bg-[#292524]/10 text-[#292524]/60 border border-[#292524]/20">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#292524]/40" />
                                        No Data
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] rounded-full bg-[#29BC41]/20 text-[#29BC41] border border-[#29BC41]/30">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#29BC41]" />
                                        Active
                                    </span>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
