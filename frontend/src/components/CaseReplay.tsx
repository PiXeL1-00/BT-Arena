"use client";

const ROLE_BORDERS: Record<string, string> = {
  Orthodox: "border-[#412AD1]/30 bg-[#412AD1]/5",
  Heretic: "border-[#B50BBB]/30 bg-[#B50BBB]/5",
  Skeptic: "border-[#FCC503]/40 bg-[#FCC503]/5",
  Judge: "border-[#29BC41]/30 bg-[#29BC41]/5",
};

interface Props {
  data: {
    case_id: string;
    messages: { role: string; model_key: string; content: string; created_at: string }[];
    results: {
      model_key: string;
      verdict: string;
      label: string;
      score: number;
      passed: boolean;
      judge_json: Record<string, unknown>;
      critical_fail_reason: string | null;
    }[];
  };
}

export function CaseReplay({ data }: Props) {
  return (
    <div className="space-y-6 w-full">
      <h1 className="text-2xl font-bold text-[#292524]">
        Case Replay: <span className="text-[#412AD1] font-mono">{data.case_id}</span>
      </h1>

      {/* Messages */}
      <div className="space-y-4">
        {data.messages.map((m, i) => (
          <div
            key={i}
            className={`glass-panel rounded-2xl p-5 border ${ROLE_BORDERS[m.role] ?? "border-[#292524]/10"}`}
          >
            <div className="flex items-center gap-2 mb-3">
              <span className="text-sm font-semibold text-[#292524]">{m.role}</span>
              <span className="text-xs text-[#292524]/60 font-mono">{m.model_key}</span>
            </div>
            <p className="text-sm text-[#292524] whitespace-pre-wrap leading-relaxed">
              {m.content}
            </p>
          </div>
        ))}
      </div>

      {/* Results */}
      <div className="glass-panel rounded-3xl p-6 shadow-lg">
        <h2 className="text-lg font-bold text-[#292524] mb-4">Scoring Results</h2>
        {data.results.map((r, i) => (
          <div key={i} className="bg-[#FFFFFF] border border-[#292524]/10 rounded-xl p-4 mb-3 shadow-sm">
            <div className="flex justify-between items-center mb-2">
              <span className="font-mono text-sm font-semibold text-[#292524]">{r.model_key}</span>
              <span
                className={`text-sm font-medium px-3 py-1 rounded-full ${r.passed
                    ? "bg-[#29BC41]/15 text-[#29BC41] border border-[#29BC41]/30"
                    : "bg-[#B50BBB]/15 text-[#B50BBB] border border-[#B50BBB]/30"
                  }`}
              >
                {r.score}/100 {r.passed ? "PASS" : "FAIL"}
              </span>
            </div>
            <p className="text-xs text-[#292524]/70">
              Verdict: {r.verdict} | Label: {r.label}
            </p>
            {r.critical_fail_reason && (
              <p className="text-xs text-[#B50BBB] font-medium mt-2">
                Critical: {r.critical_fail_reason}
              </p>
            )}
            <details className="mt-3">
              <summary className="text-xs text-[#292524]/60 cursor-pointer hover:text-[#412AD1] transition">
                Judge JSON
              </summary>
              <pre className="text-xs text-[#292524]/80 mt-2 bg-[#292524]/5 border border-[#292524]/10 p-3 rounded-lg overflow-x-auto font-mono">
                {JSON.stringify(r.judge_json, null, 2)}
              </pre>
            </details>
          </div>
        ))}
      </div>
    </div>
  );
}
