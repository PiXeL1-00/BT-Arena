"use client";

import { Trophy, Crown, Zap, DollarSign } from "lucide-react";
import type { ModelMetrics } from "@/lib/types";

interface Props {
  models: ModelMetrics[];
}

const RANK_STYLES = [
  { ring: "stroke-yellow-400", glow: "shadow-[0_0_20px_rgba(250,204,21,0.35)]", badge: "from-yellow-400 to-amber-500", label: "text-yellow-300" },
  { ring: "stroke-slate-300", glow: "shadow-[0_0_14px_rgba(203,213,225,0.25)]", badge: "from-slate-300 to-slate-400", label: "text-slate-300" },
  { ring: "stroke-amber-600", glow: "shadow-[0_0_14px_rgba(217,119,6,0.25)]", badge: "from-amber-600 to-amber-700", label: "text-amber-500" },
] as const;

function RadialProgress({ pct, rankIdx }: { pct: number; rankIdx: number }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const style = rankIdx < 3 ? RANK_STYLES[rankIdx] : null;

  return (
    <>
      <svg width={68} height={68} className="shrink-0 hidden sm:block">
        <circle cx={34} cy={34} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={4} />
        <circle
          cx={34} cy={34} r={r} fill="none"
          className={style?.ring ?? "stroke-cyan-400"}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          transform="rotate(-90 34 34)"
          style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(.4,0,.2,1)" }}
        />
        <text x={34} y={36} textAnchor="middle" className="fill-white text-[11px] font-bold">
          {pct.toFixed(0)}%
        </text>
      </svg>
      {/* Smaller mobile version */}
      <svg width={44} height={44} className="shrink-0 sm:hidden">
        <circle cx={22} cy={22} r={18} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={3} />
        <circle
          cx={22} cy={22} r={18} fill="none"
          className={style?.ring ?? "stroke-cyan-400"}
          strokeWidth={3}
          strokeLinecap="round"
          strokeDasharray={2 * Math.PI * 18}
          strokeDashoffset={2 * Math.PI * 18 - (pct / 100) * 2 * Math.PI * 18}
          transform="rotate(-90 22 22)"
          style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(.4,0,.2,1)" }}
        />
        <text x={22} y={24} textAnchor="middle" className="fill-white text-[9px] font-bold">
          {pct.toFixed(0)}%
        </text>
      </svg>
    </>
  );
}

function StatMicro({ icon: Icon, value, unit, color }: { icon: typeof Zap; value: string; unit: string; color: string }) {
  return (
    <div className="flex items-center gap-1.5 text-[10px]">
      <Icon className={`w-3 h-3 ${color}`} />
      <span className="text-white/70 font-mono">{value}</span>
      <span className="text-white/30">{unit}</span>
    </div>
  );
}

export function Leaderboard({ models }: Props) {
  const sorted = [...models].sort((a, b) => b.pass_rate - a.pass_rate);

  return (
    <div className="glass-panel rounded-2xl sm:rounded-3xl p-4 sm:p-6 relative overflow-hidden">
      <div className="absolute -top-16 -right-16 w-44 h-44 bg-gradient-radial from-cyan-500/10 to-transparent rounded-full blur-2xl pointer-events-none" />

      <div className="flex items-center gap-2 sm:gap-3 mb-3 sm:mb-5">
        <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
          <Trophy className="w-4 h-4 text-cyan-400" />
        </div>
        <h2 className="text-base sm:text-lg font-medium text-cyan-300 tracking-wide">Arena Leaderboard</h2>
      </div>

      {sorted.length === 0 ? (
        <div className="py-8 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-sm text-white/50">Awaiting evaluation results…</span>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map((m, i) => {
            const style = i < 3 ? RANK_STYLES[i] : null;
            const pct = m.pass_rate * 100;

            return (
              <div
                key={m.model_key}
                className={`relative rounded-2xl border transition-all duration-300 hover:scale-[1.01] ${style
                  ? `bg-gradient-to-r from-white/[0.06] to-white/[0.02] border-white/10 ${style.glow}`
                  : "bg-white/[0.03] border-white/5 hover:border-white/10"
                  }`}
              >
                <div className="flex items-center gap-2 sm:gap-4 p-3 sm:p-4">
                  {/* Rank badge */}
                  <div className="relative">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-xs font-black ${style ? `bg-gradient-to-br ${style.badge} text-black` : "bg-white/10 text-white/50"
                      }`}>
                      {i === 0 ? <Crown className="w-4 h-4" /> : `#${i + 1}`}
                    </div>
                    {i === 0 && (
                      <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-yellow-400 animate-ping opacity-60" />
                    )}
                  </div>

                  {/* Radial progress */}
                  <RadialProgress pct={pct} rankIdx={i} />

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-mono text-white/90 truncate">{m.model_key}</p>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${m.model_passes_eval
                        ? "bg-green-500/15 text-green-300 border border-green-500/25"
                        : "bg-red-500/15 text-red-300 border border-red-500/25"
                        }`}>
                        {m.model_passes_eval ? "PASS" : "FAIL"}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 flex-wrap">
                      <span className="text-[11px] text-white/40">
                        {m.passed_cases}/{m.total_cases} cases
                      </span>
                      <StatMicro icon={Zap} value={m.avg_latency_ms.toFixed(0)} unit="ms" color="text-yellow-400/70" />
                      <StatMicro icon={DollarSign} value={m.total_cost.toFixed(4)} unit="" color="text-emerald-400/70" />
                    </div>

                    {/* Tiny pass-rate bar */}
                    <div className="mt-2 h-1 rounded-full bg-white/5 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-1000 ${m.model_passes_eval
                          ? "bg-gradient-to-r from-green-400 to-emerald-500"
                          : "bg-gradient-to-r from-red-400 to-rose-500"
                          }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
