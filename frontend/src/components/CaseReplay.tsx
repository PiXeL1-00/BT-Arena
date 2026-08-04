"use client";

const ROLE_BORDERS: Record<string, string> = {
  Orthodox: "border-cyan-500/30 bg-gradient-to-r from-blue-500/10 to-cyan-500/10",
  Heretic: "border-rose-500/30 bg-gradient-to-r from-rose-500/10 to-orange-500/10",
  Skeptic: "border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-yellow-500/10",
  Judge: "border-emerald-500/30 bg-gradient-to-r from-emerald-500/10 to-teal-500/10",
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
      <h1 className="text-2xl font-light">
        Case Replay: <span className="text-cyan-300">{data.case_id}</span>
      </h1>

      {/* Messages */}
      <div className="space-y-4">
        {data.messages.map((m, i) => (
          <div
            key={i}
            className={`glass-panel rounded-2xl p-5 border ${ROLE_BORDERS[m.role] ?? "border-white/10"}`}
          >
            <div className="flex items-center gap-2 mb-3">
              <span className="text-sm font-medium text-white/90">{m.role}</span>
              <span className="text-xs text-white/50 font-mono">{m.model_key}</span>
            </div>
            <p className="text-sm text-white/80 whitespace-pre-wrap leading-relaxed">
              {m.content}
            </p>
          </div>
        ))}
      </div>

      {/* Results */}
      <div className="glass-panel rounded-3xl p-6">
        <h2 className="text-lg font-medium mb-4">Scoring Results</h2>
        {data.results.map((r, i) => (
          <div key={i} className="glass-button rounded-xl p-4 mb-3">
            <div className="flex justify-between items-center mb-2">
              <span className="font-mono text-sm text-white/90">{r.model_key}</span>
              <span
                className={`text-sm font-medium px-3 py-1 rounded-full ${r.passed
                    ? "bg-green-500/20 text-green-300 border border-green-500/30"
                    : "bg-red-500/20 text-red-300 border border-red-500/30"
                  }`}
              >
                {r.score}/100 {r.passed ? "PASS" : "FAIL"}
              </span>
            </div>
            <p className="text-xs text-white/60">
              Verdict: {r.verdict} | Label: {r.label}
            </p>
            {r.critical_fail_reason && (
              <p className="text-xs text-red-300 mt-2">
                Critical: {r.critical_fail_reason}
              </p>
            )}
            <details className="mt-3">
              <summary className="text-xs text-white/50 cursor-pointer hover:text-white/70 transition">
                Judge JSON
              </summary>
              <pre className="text-xs text-white/60 mt-2 glass-button p-3 rounded-lg overflow-x-auto">
                {JSON.stringify(r.judge_json, null, 2)}
              </pre>
            </details>
          </div>
        ))}
      </div>
    </div>
  );
}
