"use client";

import { useState, useMemo, Suspense, lazy } from "react";
import { BarChart3, Shield, Settings, Box } from "lucide-react";
import {
    useModelsSummary, useModelsTrend, useDistribution,
    useUplift, useFailures, usePareto,
    useScoreBreakdown, useRadar, useHeatmap,
    useHallucinationTrend, useCalibrationScatter, useCostPerPass,
} from "@/lib/galileoQueries";
import { useDatasets } from "@/lib/queries";
import type { GalileoQueryParams } from "@/lib/galileoApi";
import ModelsTable from "@/components/analytics/ModelsTable";
import { GlassCard } from "@/components/ui/GlassCard";
import { NeonSpinner } from "@/components/ui/NeonSpinner";
import type { LucideIcon } from "lucide-react";

const TrendChart = lazy(() => import("@/components/analytics/TrendChart"));
const DistributionChart = lazy(() => import("@/components/analytics/DistributionChart"));
const ScoreBreakdownChart = lazy(() => import("@/components/analytics/ScoreBreakdownChart"));
const RadarChart = lazy(() => import("@/components/analytics/RadarChart"));
const HeatmapChart = lazy(() => import("@/components/analytics/HeatmapChart"));
const HallucinationTrendChart = lazy(() => import("@/components/analytics/HallucinationTrendChart"));
const CalibrationScatter = lazy(() => import("@/components/analytics/CalibrationScatter"));
const CostPerPassChart = lazy(() => import("@/components/analytics/CostPerPassChart"));

const ParetoNebula3D = lazy(() => import("@/components/three/ParetoNebula3D"));
const TrendCurrents3D = lazy(() => import("@/components/three/TrendCurrents3D"));

const TAB_PERFORMANCE = "performance";
const TAB_ROBUSTNESS = "robustness";
const TAB_EFFECTIVENESS = "effectiveness";
const TAB_OPS = "ops";
const TAB_3D = "3d";

interface TabDef {
    id: string;
    label: string;
    icon: LucideIcon;
}

const TABS: TabDef[] = [
    { id: TAB_PERFORMANCE, label: "Performance", icon: BarChart3 },
    { id: TAB_ROBUSTNESS, label: "Robustness", icon: Shield },
    // { id: TAB_EFFECTIVENESS, label: "Galileo Effect", icon: Microscope },  // TODO: re-enable when baseline mode is implemented
    { id: TAB_OPS, label: "Operations", icon: Settings },
    { id: TAB_3D, label: "3D Arena", icon: Box },
];

const WINDOW_OPTIONS = [7, 14, 30, 90] as const;

export default function GraphsPage() {
    const [activeTab, setActiveTab] = useState(TAB_PERFORMANCE);
    const [window, setWindow] = useState<number>(30);

    const params: GalileoQueryParams = useMemo(
        () => ({ window, includeScheduled: true }),
        [window],
    );

    const { data: summaryData, isLoading: summaryLoading } = useModelsSummary(params);
    const { data: trendData, isLoading: trendLoading } = useModelsTrend(params);

    const modelNames = useMemo(() => {
        const map = new Map<string, string>();
        if (summaryData?.models) {
            for (const m of summaryData.models) {
                map.set(m.llm_id, m.display_name);
            }
        }
        return map;
    }, [summaryData]);

    return (
        <div className="min-h-screen text-white pt-16">
            <div className="max-w-7xl mx-auto px-4 pt-4 pb-2 flex items-center justify-end gap-3">
                <select
                    value={window}
                    onChange={(e) => setWindow(Number(e.target.value))}
                    className="bg-white/[0.04] border border-white/[0.06] rounded-lg px-3 py-1.5 text-sm text-white/60 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 transition-all"
                >
                    {WINDOW_OPTIONS.map((w) => (
                        <option key={w} value={w}>{w}d window</option>
                    ))}
                </select>
            </div>

            <div className="max-w-7xl mx-auto px-4 py-6">
                <div className="overflow-x-auto hide-scrollbar -mx-4 px-4 mb-6">
                    <div className="flex gap-0 border-b border-white/[0.06] min-w-max">
                        {TABS.map((tab) => {
                            const Icon = tab.icon;
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`relative px-4 sm:px-5 py-3 text-sm font-medium transition-all duration-300 flex items-center gap-2 whitespace-nowrap ${activeTab === tab.id
                                        ? "text-cyan-300"
                                        : "text-white/35 hover:text-white/60"
                                        }`}
                                >
                                    <Icon className="w-4 h-4" />
                                    {tab.label}
                                    {activeTab === tab.id && (
                                        <span className="absolute bottom-0 left-2 right-2 h-[2px] bg-gradient-to-r from-cyan-400 to-teal-400 rounded-full" />
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </div>

                <Suspense fallback={<NeonSpinner className="h-64" />}>
                    {activeTab === TAB_PERFORMANCE && (
                        <PerformanceTab params={params} modelNames={modelNames} summaryData={summaryData} trendData={trendData} />
                    )}
                    {activeTab === TAB_ROBUSTNESS && (
                        <RobustnessTab params={params} modelNames={modelNames} />
                    )}
                    {/* TODO: re-enable when baseline mode is implemented
                    {activeTab === TAB_EFFECTIVENESS && (
                        <EffectivenessTab params={params} modelNames={modelNames} />
                    )}
                    */}
                    {activeTab === TAB_OPS && (
                        <OpsTab params={params} modelNames={modelNames} />
                    )}
                    {activeTab === TAB_3D && (
                        <ThreeDTab params={params} modelNames={modelNames} />
                    )}
                </Suspense>
            </div>
        </div>
    );
}

interface TabProps {
    params: GalileoQueryParams;
    modelNames: Map<string, string>;
}

interface PerformanceTabProps extends TabProps {
    summaryData: ReturnType<typeof useModelsSummary>["data"];
    trendData: ReturnType<typeof useModelsTrend>["data"];
}

function PerformanceTab({ params, modelNames, summaryData, trendData }: PerformanceTabProps) {
    const { data: distData } = useDistribution(params);
    const { data: breakdownData } = useScoreBreakdown(params);
    const { data: radarData } = useRadar(params);

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <GlassCard expandable title="Score Trend">
                    <div className="min-h-[300px] h-[300px]">
                        {trendData?.series?.length ? (
                            <TrendChart series={trendData.series} modelNames={modelNames} />
                        ) : (
                            <NeonSpinner className="h-64" />
                        )}
                    </div>
                </GlassCard>
                <GlassCard expandable title="Score Distribution">
                    <div className="min-h-[300px] h-[300px]">
                        {distData?.items?.length ? (
                            <DistributionChart items={distData.items} modelNames={modelNames} />
                        ) : (
                            <NeonSpinner className="h-64" />
                        )}
                    </div>
                </GlassCard>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <GlassCard expandable title="Score Breakdown">
                    <div className="min-h-[300px] h-[300px]">
                        {breakdownData?.items?.length ? (
                            <ScoreBreakdownChart items={breakdownData.items} modelNames={modelNames} />
                        ) : (
                            <div className="text-gray-500 h-full flex items-center justify-center">No breakdown data</div>
                        )}
                    </div>
                </GlassCard>
                <GlassCard expandable title="Radar / Spider">
                    <div className="min-h-[300px] h-[300px]">
                        {radarData?.entries?.length ? (
                            <RadarChart entries={radarData.entries} modelNames={modelNames} />
                        ) : (
                            <div className="text-gray-500 h-full flex items-center justify-center">No radar data</div>
                        )}
                    </div>
                </GlassCard>
            </div>
            <GlassCard expandable title="All Models">
                {summaryData?.models ? (
                    <ModelsTable models={summaryData.models} windowDays={params.window ?? 30} />
                ) : (
                    <NeonSpinner className="h-64" />
                )}
            </GlassCard>
        </div>
    );
}

function RobustnessTab({ params, modelNames }: TabProps) {
    const { data: distData } = useDistribution(params);
    const { data: hallucinationData } = useHallucinationTrend(params);
    const { data: calibrationData } = useCalibrationScatter(params);

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <GlassCard expandable title="Hallucination Rate Trend">
                    {hallucinationData?.series?.length ? (
                        <HallucinationTrendChart series={hallucinationData.series} modelNames={modelNames} />
                    ) : (
                        <div className="text-gray-500 h-32 flex items-center justify-center">No hallucination data</div>
                    )}
                </GlassCard>
                <GlassCard expandable title="Confidence vs Correctness">
                    {calibrationData?.points?.length ? (
                        <CalibrationScatter points={calibrationData.points} modelNames={modelNames} />
                    ) : (
                        <div className="text-gray-500 h-32 flex items-center justify-center">No calibration data</div>
                    )}
                </GlassCard>
            </div>
            <GlassCard expandable title="Score Stability (σ)">
                {distData?.items?.length ? (
                    (() => {
                        const filtered = distData.items
                            .filter((d) => d.stddev !== null)
                            .sort((a, b) => (a.stddev ?? 0) - (b.stddev ?? 0));
                        const maxStddev = Math.max(...filtered.map((d) => d.stddev ?? 0), 0.01);
                        return (
                            <div className="space-y-3">
                                {filtered.map((d, i) => (
                                    <div key={d.llm_id} className="flex items-center gap-3 group/row">
                                        <span className="text-xs font-mono text-cyan-500/60 w-5">{i + 1}</span>
                                        <span className="text-sm text-gray-300 w-20 sm:w-32 truncate group-hover/row:text-white transition-colors">
                                            {modelNames.get(d.llm_id) ?? d.llm_id.slice(0, 8)}
                                        </span>
                                        <div className="flex-1 bg-slate-800/60 rounded-full h-2.5 overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-amber-400 rounded-full transition-all shadow-[0_0_8px_rgba(34,211,238,0.3)]"
                                                style={{ width: `${((d.stddev ?? 0) / maxStddev) * 100}%` }}
                                            />
                                        </div>
                                        <span className="text-xs text-gray-500 font-mono w-12 text-right">
                                            {d.stddev?.toFixed(2) ?? "—"}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        );
                    })()
                ) : (
                    <div className="text-gray-500 h-32 flex items-center justify-center">No stability data</div>
                )}
            </GlassCard>
        </div>
    );
}

function EffectivenessTab({ params, modelNames }: TabProps) {
    const { data: upliftData } = useUplift(params);

    return (
        <div className="space-y-6">
            <GlassCard expandable title="Galileo Effect (Uplift)">
                {upliftData?.items?.length ? (
                    <div className="space-y-4">
                        {upliftData.items
                            .sort((a, b) => (b.delta ?? 0) - (a.delta ?? 0))
                            .map((u) => (
                                <div key={u.llm_id} className="flex items-center gap-4">
                                    <span className="text-sm text-gray-300 w-40 truncate">
                                        {modelNames.get(u.llm_id) ?? u.llm_id.slice(0, 8)}
                                    </span>
                                    <div className="flex-1 flex items-center gap-3">
                                        <span className="text-xs text-gray-500 font-mono">
                                            Baseline: {u.avg_baseline?.toFixed(2) ?? "—"}
                                        </span>
                                        <span className="text-lg">→</span>
                                        <span className="text-xs text-cyan-300 font-mono">
                                            Galileo: {u.avg_galileo?.toFixed(2) ?? "—"}
                                        </span>
                                        <span className={`text-sm font-bold ${(u.delta ?? 0) > 0 ? "text-emerald-400" : (u.delta ?? 0) < 0 ? "text-rose-400" : "text-gray-400"
                                            }`}>
                                            {u.delta !== null ? `${u.delta > 0 ? "+" : ""}${u.delta.toFixed(2)}` : "—"}
                                        </span>
                                    </div>
                                    <span className="text-xs text-gray-500">{u.n_pairs} pairs</span>
                                </div>
                            ))}
                    </div>
                ) : (
                    <div className="text-gray-500 h-32 flex items-center justify-center">
                        No uplift data — run baseline + galileo evaluations with shared batch_id
                    </div>
                )}
            </GlassCard>
        </div>
    );
}

function OpsTab({ params, modelNames }: TabProps) {
    const { data: paretoData } = usePareto(params);
    const { data: costData } = useCostPerPass(params);


    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <GlassCard expandable title="Score vs Latency (Pareto)">
                    {paretoData?.items?.length ? (
                        <div className="space-y-1">
                            {paretoData.items
                                .sort((a, b) => (b.avg_score ?? 0) - (a.avg_score ?? 0))
                                .map((p, i) => (
                                    <div key={p.llm_id} className="flex items-center gap-4 py-2.5 border-b border-white/[0.04] hover:bg-white/[0.03] rounded-lg px-2 -mx-2 transition-colors group/row">
                                        <span className="text-xs font-bold w-6 h-6 flex items-center justify-center rounded-md bg-gradient-to-br from-cyan-500/20 to-teal-500/20 text-cyan-400 border border-cyan-500/20">
                                            {i + 1}
                                        </span>
                                        <span className="text-sm text-gray-300 w-20 sm:w-36 truncate group-hover/row:text-white transition-colors">
                                            {modelNames.get(p.llm_id) ?? p.llm_id.slice(0, 8)}
                                        </span>
                                        <div className="flex-1 grid grid-cols-3 gap-2 sm:gap-4 text-xs font-mono">
                                            <div className="flex flex-col">
                                                <span className="text-[10px] text-gray-600 uppercase tracking-wider">Score</span>
                                                <span className="text-cyan-300 drop-shadow-[0_0_4px_rgba(34,211,238,0.4)]">{p.avg_score?.toFixed(2) ?? "—"}</span>
                                            </div>
                                            <div className="flex flex-col">
                                                <span className="text-[10px] text-gray-600 uppercase tracking-wider">Latency</span>
                                                <span className="text-amber-300 drop-shadow-[0_0_4px_rgba(245,158,11,0.4)]">
                                                    {p.avg_latency_ms ? `${Math.round(p.avg_latency_ms)}ms` : "—"}
                                                </span>
                                            </div>
                                            <div className="flex flex-col">
                                                <span className="text-[10px] text-gray-600 uppercase tracking-wider">Cost</span>
                                                <span className="text-emerald-300 drop-shadow-[0_0_4px_rgba(52,211,153,0.4)]">
                                                    {p.avg_cost_usd !== null ? `$${Number(p.avg_cost_usd).toFixed(4)}` : "—"}
                                                </span>
                                            </div>
                                        </div>
                                        <span className="text-[10px] text-gray-600 font-mono tabular-nums">{p.n} runs</span>
                                    </div>
                                ))}
                        </div>
                    ) : (
                        <div className="text-gray-500 h-32 flex items-center justify-center">No operations data</div>
                    )}
                </GlassCard>
                <GlassCard expandable title="Cost per Passing Answer">
                    {costData?.items?.length ? (
                        <CostPerPassChart items={costData.items} modelNames={modelNames} />
                    ) : (
                        <div className="text-gray-500 h-32 flex items-center justify-center">No cost data</div>
                    )}
                </GlassCard>
            </div>

        </div>
    );
}

function ThreeDTab({ params, modelNames }: TabProps) {
    const { data: paretoData } = usePareto(params);
    const { data: trendData } = useModelsTrend(params);

    return (
        <div className="space-y-6">
            <GlassCard expandable title="Pareto Nebula — Score × Latency × Cost">
                <div className="min-h-[400px] h-[400px]">
                    {paretoData?.items?.length ? (
                        <ParetoNebula3D items={paretoData.items} modelNames={modelNames} />
                    ) : (
                        <NeonSpinner className="h-64" />
                    )}
                </div>
            </GlassCard>
            <GlassCard expandable title="Trend Currents — Score Over Time">
                <div className="min-h-[400px] h-[400px]">
                    {trendData?.series?.length ? (
                        <TrendCurrents3D series={trendData.series} modelNames={modelNames} />
                    ) : (
                        <NeonSpinner className="h-64" />
                    )}
                </div>
            </GlassCard>
        </div>
    );
}
