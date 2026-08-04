"use client";

import { useMemo, Suspense, lazy } from "react";
import { useDashboard } from "@/lib/galileoQueries";
import type { GalileoQueryParams } from "@/lib/galileoApi";
import { GlassCard } from "@/components/ui/GlassCard";
import { NeonSpinner } from "@/components/ui/NeonSpinner";

const TrendChart = lazy(() => import("@/components/analytics/TrendChart"));
const DistributionChart = lazy(() => import("@/components/analytics/DistributionChart"));
const ScoreBreakdownChart = lazy(() => import("@/components/analytics/ScoreBreakdownChart"));
const RadarChart = lazy(() => import("@/components/analytics/RadarChart"));

const PARAMS: GalileoQueryParams = { window: 30, includeScheduled: true };

export default function StartDashboard() {
    const { data } = useDashboard(PARAMS);

    const modelNames = useMemo(() => {
        const map = new Map<string, string>();
        if (data?.summary?.models) {
            for (const m of data.summary.models) {
                map.set(m.llm_id, m.display_name);
            }
        }
        return map;
    }, [data?.summary]);

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 sm:grid-rows-2 gap-3 h-full">
            <GlassCard title="Score Trend" size="sm" className="min-h-[200px] sm:min-h-0">
                <Suspense fallback={<NeonSpinner />}>
                    {data?.trend?.series?.length ? (
                        <TrendChart series={data.trend.series} modelNames={modelNames} />
                    ) : (
                        <NeonSpinner />
                    )}
                </Suspense>
            </GlassCard>

            <GlassCard title="Distribution" size="sm" className="min-h-[200px] sm:min-h-0">
                <Suspense fallback={<NeonSpinner />}>
                    {data?.distribution?.items?.length ? (
                        <DistributionChart items={data.distribution.items} modelNames={modelNames} />
                    ) : (
                        <NeonSpinner />
                    )}
                </Suspense>
            </GlassCard>

            <GlassCard title="Breakdown" size="sm" className="min-h-[200px] sm:min-h-0">
                <Suspense fallback={<NeonSpinner />}>
                    {data?.breakdown?.items?.length ? (
                        <ScoreBreakdownChart items={data.breakdown.items} modelNames={modelNames} />
                    ) : (
                        <NeonSpinner />
                    )}
                </Suspense>
            </GlassCard>

            <GlassCard title="Radar" size="sm" className="min-h-[200px] sm:min-h-0">
                <Suspense fallback={<NeonSpinner />}>
                    {data?.radar?.entries?.length ? (
                        <RadarChart entries={data.radar.entries} modelNames={modelNames} />
                    ) : (
                        <NeonSpinner />
                    )}
                </Suspense>
            </GlassCard>
        </div>
    );
}
