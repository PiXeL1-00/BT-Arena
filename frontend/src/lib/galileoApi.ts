/* Galileo analytics API client. */

import { API_BASE } from "./constants";
import type {
    ModelsSummaryResponse,
    TrendResponse,
    DistributionResponse,
    HeatmapResponse,
    RadarResponse,
    UpliftResponse,
    FailuresResponse,
    ParetoResponse,
    ScoreBreakdownResponse,
    HallucinationTrendResponse,
    CalibrationResponse,
    CostPerPassResponse,
    DashboardResponse,
} from "./galileoTypes";

async function fetchGalileo<T>(path: string): Promise<T> {
    const res = await fetch(`${API_BASE}/galileo${path}`);
    if (!res.ok) throw new Error(`Galileo API ${res.status}: ${await res.text()}`);
    return res.json() as Promise<T>;
}

export interface GalileoQueryParams {
    window?: number;
    includeScheduled?: boolean;
    llmIds?: string[];
    evalMode?: string;
}

function buildQs(params: GalileoQueryParams, extra?: Record<string, string>): string {
    const qs = new URLSearchParams();
    if (params.window) qs.set("window", String(params.window));
    if (params.includeScheduled) qs.set("include_scheduled", "true");
    if (params.llmIds?.length) qs.set("llm_ids", params.llmIds.join(","));
    if (params.evalMode) qs.set("eval_mode", params.evalMode);
    if (extra) {
        for (const [k, v] of Object.entries(extra)) qs.set(k, v);
    }
    return qs.toString() ? `?${qs}` : "";
}

export const galileoApi = {
    async getDashboard(params: GalileoQueryParams = {}): Promise<DashboardResponse> {
        return fetchGalileo(`/dashboard${buildQs(params)}`);
    },

    async getModelsSummary(params: GalileoQueryParams = {}): Promise<ModelsSummaryResponse> {
        return fetchGalileo(`/models/summary${buildQs(params)}`);
    },

    async getModelsTrend(params: GalileoQueryParams = {}): Promise<TrendResponse> {
        return fetchGalileo(`/models/trend${buildQs(params)}`);
    },

    async getDistribution(params: GalileoQueryParams = {}): Promise<DistributionResponse> {
        return fetchGalileo(`/models/distribution${buildQs(params)}`);
    },

    async getHeatmap(
        datasetId: string,
        params: GalileoQueryParams & { topK?: number } = {},
    ): Promise<HeatmapResponse> {
        const extra: Record<string, string> = { dataset_id: datasetId };
        if (params.topK) extra["top_k"] = String(params.topK);
        return fetchGalileo(`/heatmap/model_case${buildQs(params, extra)}`);
    },

    async getRadar(params: GalileoQueryParams = {}): Promise<RadarResponse> {
        return fetchGalileo(`/dimensions/radar${buildQs(params)}`);
    },

    async getUplift(params: GalileoQueryParams = {}): Promise<UpliftResponse> {
        return fetchGalileo(`/effect/uplift${buildQs(params)}`);
    },

    async getFailures(params: GalileoQueryParams = {}): Promise<FailuresResponse> {
        return fetchGalileo(`/failures/breakdown${buildQs(params)}`);
    },

    async getPareto(params: GalileoQueryParams = {}): Promise<ParetoResponse> {
        return fetchGalileo(`/ops/pareto${buildQs(params)}`);
    },

    async getScoreBreakdown(params: GalileoQueryParams = {}): Promise<ScoreBreakdownResponse> {
        return fetchGalileo(`/dimensions/breakdown${buildQs(params)}`);
    },

    async getHallucinationTrend(params: GalileoQueryParams = {}): Promise<HallucinationTrendResponse> {
        return fetchGalileo(`/hallucination/trend${buildQs(params)}`);
    },

    async getCalibrationScatter(params: GalileoQueryParams = {}): Promise<CalibrationResponse> {
        return fetchGalileo(`/calibration/scatter${buildQs(params)}`);
    },

    async getCostPerPass(params: GalileoQueryParams = {}): Promise<CostPerPassResponse> {
        return fetchGalileo(`/ops/cost_per_pass${buildQs(params)}`);
    },
};
