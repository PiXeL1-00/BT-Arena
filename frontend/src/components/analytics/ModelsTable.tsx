"use client";

import type { ModelSummaryItem } from "@/lib/galileoTypes";

interface ModelsTableProps {
    models: ModelSummaryItem[];
    windowDays: number;
}

const RANK_COLORS = [
    "from-yellow-400/30 to-yellow-500/10 border-yellow-500/30 text-yellow-300",
    "from-slate-300/20 to-slate-400/10 border-slate-400/30 text-slate-300",
    "from-amber-600/20 to-amber-700/10 border-amber-600/30 text-amber-400",
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
            <div className="flex items-center justify-center h-32 text-gray-500">
                No models configured
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-cyan-500/10 text-gray-500 text-[10px] uppercase tracking-[0.15em]">
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
                            className="border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors group/row"
                        >
                            <td className="text-center py-3 px-2">
                                <span className={`inline-flex items-center justify-center w-6 h-6 rounded-md text-[10px] font-bold bg-gradient-to-br border ${i < 3 ? RANK_COLORS[i] : "from-slate-700/30 to-slate-800/20 border-white/5 text-gray-600"}`}>
                                    {i + 1}
                                </span>
                            </td>
                            <td className="py-3 px-2">
                                <span className="font-medium text-white group-hover/row:text-cyan-200 transition-colors">{m.display_name}</span>
                                <span className="ml-2 text-[10px] text-gray-600">{m.provider}</span>
                            </td>
                            <td className="text-right py-3 px-2">
                                <span className="font-mono text-cyan-300 drop-shadow-[0_0_4px_rgba(34,211,238,0.3)]">
                                    {formatScore(m.all_time_avg)}
                                </span>
                            </td>
                            <td className="text-right py-3 px-2">
                                <span className="font-mono text-emerald-300 drop-shadow-[0_0_4px_rgba(52,211,153,0.3)]">
                                    {formatScore(m.window_avg)}
                                </span>
                            </td>
                            <td className="text-right py-3 px-2 font-mono text-gray-400 tabular-nums">
                                {m.all_time_runs}
                            </td>
                            <td className="text-right py-3 px-2 text-gray-500 text-xs">
                                {formatDate(m.last_run_at)}
                            </td>
                            <td className="text-center py-3 px-2">
                                {m.is_stale ? (
                                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/20">
                                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shadow-[0_0_4px_rgba(251,191,36,0.6)]" />
                                        Stale
                                    </span>
                                ) : m.all_time_runs === 0 ? (
                                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] rounded-full bg-gray-500/15 text-gray-400 border border-gray-500/20">
                                        <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
                                        No Data
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
                                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.6)]" />
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
