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
    <div className="glass-panel rounded-3xl p-6">
      <h2 className="text-lg font-medium text-red-300 mb-4">
        Recent Failures ({failures.length})
      </h2>
      <div className="space-y-3">
        {failures.map((f, i) => (
          <Link
            key={i}
            href={`/run/${runId}/case/${f.case_id}`}
            className="block glass-button rounded-xl p-3 transition"
          >
            <div className="flex justify-between items-center">
              <span className="text-xs font-mono text-white/60">{f.case_id}</span>
              <span className="text-xs text-red-300 font-medium">
                {f.score}/100
              </span>
            </div>
            <p className="text-xs text-white/50 mt-2">
              {f.model_key} &middot; {f.verdict}
              {f.critical_fail_reason && (
                <span className="text-red-300 ml-2">
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
