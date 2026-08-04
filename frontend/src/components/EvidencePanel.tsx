"use client";

import { FileText, ExternalLink, Calendar } from "lucide-react";
import type { Evidence } from "@/lib/types";

interface Props {
    evidences: Evidence[];
}

function EvidenceCard({ ev, idx }: { ev: Evidence; idx: number }) {
    return (
        <div className="relative rounded-xl border border-white/8 bg-white/[0.03] hover:bg-white/[0.06] transition-all duration-200 p-4 group">
            <div className="flex items-start gap-3">
                <div className="shrink-0 w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/20 flex items-center justify-center text-[10px] font-bold text-indigo-300 font-mono">
                    {ev.eid}
                </div>

                <div className="flex-1 min-w-0">
                    <p className="text-sm text-white/80 leading-relaxed mb-2">
                        {ev.summary}
                    </p>

                    <div className="flex items-center gap-4 flex-wrap text-[10px]">
                        {ev.source && (
                            <span className="flex items-center gap-1 text-white/40">
                                <ExternalLink className="w-3 h-3 text-cyan-400/60" />
                                <span className="truncate max-w-[180px]">{ev.source}</span>
                            </span>
                        )}
                        {ev.date && (
                            <span className="flex items-center gap-1 text-white/40">
                                <Calendar className="w-3 h-3 text-amber-400/60" />
                                {ev.date}
                            </span>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export function EvidencePanel({ evidences }: Props) {
    if (evidences.length === 0) return null;

    return (
        <div className="glass-panel rounded-2xl sm:rounded-3xl p-4 sm:p-6 relative overflow-hidden">
            <div className="absolute -bottom-12 -left-12 w-36 h-36 bg-gradient-radial from-indigo-500/10 to-transparent rounded-full blur-2xl pointer-events-none" />

            <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
                    <FileText className="w-4 h-4 text-indigo-400" />
                </div>
                <div>
                    <h2 className="text-lg font-medium text-indigo-300 tracking-wide">Evidence Packets</h2>
                    <p className="text-[10px] text-white/30 mt-0.5">{evidences.length} source{evidences.length !== 1 ? "s" : ""} provided</p>
                </div>
            </div>

            <div className="space-y-2">
                {evidences.map((ev, i) => (
                    <EvidenceCard key={ev.eid} ev={ev} idx={i} />
                ))}
            </div>
        </div>
    );
}
