/* TanStack Query hooks for galileo analytics. */

import { useQuery } from "@tanstack/react-query";
import { galileoApi, type GalileoQueryParams } from "./galileoApi";

const STALE_60S = 60 * 1000;
const STALE_5M = 5 * 60 * 1000;

export const galileoKeys = {
    dashboard: (p: GalileoQueryParams) => ["galileo", "dashboard", p] as const,
    summary: (p: GalileoQueryParams) => ["galileo", "summary", p] as const,
    trend: (p: GalileoQueryParams) => ["galileo", "trend", p] as const,
    distribution: (p: GalileoQueryParams) => ["galileo", "distribution", p] as const,
    heatmap: (dsId: string, p: GalileoQueryParams) => ["galileo", "heatmap", dsId, p] as const,
    radar: (p: GalileoQueryParams) => ["galileo", "radar", p] as const,
    uplift: (p: GalileoQueryParams) => ["galileo", "uplift", p] as const,
    failures: (p: GalileoQueryParams) => ["galileo", "failures", p] as const,
    pareto: (p: GalileoQueryParams) => ["galileo", "pareto", p] as const,
    scoreBreakdown: (p: GalileoQueryParams) => ["galileo", "scoreBreakdown", p] as const,
    hallucinationTrend: (p: GalileoQueryParams) => ["galileo", "hallucinationTrend", p] as const,
    calibration: (p: GalileoQueryParams) => ["galileo", "calibration", p] as const,
    costPerPass: (p: GalileoQueryParams) => ["galileo", "costPerPass", p] as const,
};

export function useDashboard(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.dashboard(params),
        queryFn: () => galileoApi.getDashboard(params),
        staleTime: STALE_60S,
    });
}

export function useModelsSummary(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.summary(params),
        queryFn: () => galileoApi.getModelsSummary(params),
        staleTime: STALE_60S,
    });
}

export function useModelsTrend(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.trend(params),
        queryFn: () => galileoApi.getModelsTrend(params),
        staleTime: STALE_60S,
    });
}

export function useDistribution(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.distribution(params),
        queryFn: () => galileoApi.getDistribution(params),
        staleTime: STALE_5M,
    });
}

export function useHeatmap(
    datasetId: string | null,
    params: GalileoQueryParams & { topK?: number } = {},
) {
    return useQuery({
        queryKey: galileoKeys.heatmap(datasetId ?? "", params),
        queryFn: () => galileoApi.getHeatmap(datasetId!, params),
        enabled: !!datasetId,
        staleTime: STALE_5M,
    });
}

export function useRadar(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.radar(params),
        queryFn: () => galileoApi.getRadar(params),
        staleTime: STALE_5M,
    });
}

export function useUplift(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.uplift(params),
        queryFn: () => galileoApi.getUplift(params),
        staleTime: STALE_5M,
    });
}

export function useFailures(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.failures(params),
        queryFn: () => galileoApi.getFailures(params),
        staleTime: STALE_5M,
    });
}

export function usePareto(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.pareto(params),
        queryFn: () => galileoApi.getPareto(params),
        staleTime: STALE_5M,
    });
}

export function useScoreBreakdown(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.scoreBreakdown(params),
        queryFn: () => galileoApi.getScoreBreakdown(params),
        staleTime: STALE_5M,
    });
}

export function useHallucinationTrend(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.hallucinationTrend(params),
        queryFn: () => galileoApi.getHallucinationTrend(params),
        staleTime: STALE_5M,
    });
}

export function useCalibrationScatter(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.calibration(params),
        queryFn: () => galileoApi.getCalibrationScatter(params),
        staleTime: STALE_5M,
    });
}

export function useCostPerPass(params: GalileoQueryParams = {}) {
    return useQuery({
        queryKey: galileoKeys.costPerPass(params),
        queryFn: () => galileoApi.getCostPerPass(params),
        staleTime: STALE_5M,
    });
}

