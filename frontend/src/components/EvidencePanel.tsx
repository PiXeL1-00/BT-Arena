"use client";

import { FileText, ExternalLink, Calendar } from "lucide-react";
import type { Evidence } from "@/lib/types";

interface Props {
    evidences: Evidence[];
}

function EvidenceCard({ ev, idx }: { ev: Evidence; idx: number }) {
    return (
        <div className="relative rounded-xl border border-[#292524]/10 bg-[#FFFFFF] hover:border-[#412AD1]/30 transition-all duration-200 p-4 group shadow-sm">
            <div className="flex items-start gap-3">
                <div className="shrink-0 w-16 h-8 rounded-lg bg-[#412AD1]/10 border border-[#412AD1]/20 flex items-center justify-center text-[10px] font-bold text-[#412AD1] font-mono">
                    {ev.eid}
                </div>

                <div className="flex-1 min-w-0">
                    <p className="text-sm text-[#292524] leading-relaxed mb-2">
                        {ev.summary}
                    </p>

                    <div className="flex items-center gap-4 flex-wrap text-[10px]">
                        {ev.source && (
                            <span className="flex items-center gap-1 text-[#292524]/60">
                                <ExternalLink className="w-3 h-3 text-[#412AD1]" />
                                <span className="truncate max-w-[180px] font-mono">{ev.source}</span>
                            </span>
                        )}
                        {ev.date && (
                            <span className="flex items-center gap-1 text-[#292524]/60">
                                <Calendar className="w-3 h-3 text-[#FCC503]" />
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
        <div className="glass-panel rounded-2xl sm:rounded-3xl p-4 sm:p-6 relative overflow-hidden shadow-lg">
            <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-[#412AD1]/10 border border-[#412AD1]/20">
                    <FileText className="w-4 h-4 text-[#412AD1]" />
                </div>
                <div>
                    <h2 className="text-lg font-bold text-[#292524] tracking-wide">Evidence Packets</h2>
                    <p className="text-[10px] text-[#292524]/60 mt-0.5">{evidences.length} source{evidences.length !== 1 ? "s" : ""} provided</p>
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
