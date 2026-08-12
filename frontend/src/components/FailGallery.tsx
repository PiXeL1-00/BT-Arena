"use client";

import Link from "next/link";
import type { CaseResult } from "@/lib/types";

interface Props {
  runId: string;
  results: CaseResult[];
}

export function FailGallery({ runId, results }: Props) {
  const failures = results.filter((r) => !r.passed).slice(0, 8);

  if (failures.length === 0) return null;

  return (
    <div className="glass-panel rounded-3xl p-6 shadow-lg">
      <h2 className="text-lg font-bold text-[#B50BBB] mb-4">
        Recent Failures ({failures.length})
      </h2>
      <div className="space-y-3">
        {failures.map((f, i) => (
          <Link
            key={i}
            href={`/run/${runId}/case/${f.case_id}`}
            className="block bg-[#FFFFFF] border border-[#292524]/10 rounded-xl p-3 hover:border-[#B50BBB]/40 transition shadow-sm"
          >
            <div className="flex justify-between items-center">
              <span className="text-xs font-mono font-semibold text-[#292524]">{f.case_id}</span>
              <span className="text-xs text-[#B50BBB] font-bold">
                {f.score}/100
              </span>
            </div>
            <p className="text-xs text-[#292524]/60 mt-2">
              {f.model_key} &middot; {f.verdict}
              {f.critical_fail_reason && (
                <span className="text-[#B50BBB] font-medium ml-2 block sm:inline">
                  CRITICAL: {f.critical_fail_reason.slice(0, 40)}
                </span>
              )}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
