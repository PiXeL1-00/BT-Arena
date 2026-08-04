/* Galileo analytics types — matches backend Pydantic schemas. */

export interface ModelSummaryItem {
    llm_id: string;
    provider: string;
    model_name: string;
    display_name: string;
    is_active: boolean;
    all_time_avg: number | null;
    all_time_runs: number;
    last_run_at: string | null;
    window_avg: number | null;
    window_runs: number;
    is_stale: boolean;
}

export interface ModelsSummaryResponse {
    models: ModelSummaryItem[];
    window_days: number;
    include_scheduled: boolean;
}

export interface TrendBucket {
    bucket: string;
    score_avg: number | null;
    n: number;
}

export interface ModelTrendSeries {
    llm_id: string;
    buckets: TrendBucket[];
}

export interface TrendResponse {
    series: ModelTrendSeries[];
    window_days: number;
}

export interface DistributionItem {
    llm_id: string;
    mean: number | null;
    stddev: number | null;
    n: number;
    p10: number | null;
    p25: number | null;
    p50: number | null;
    p75: number | null;
    p90: number | null;
}

export interface DistributionResponse {
    items: DistributionItem[];
}

export interface HeatmapCell {
    llm_id: string;
    case_id: string;
    avg_score: number | null;
    n: number;
}

export interface HeatmapResponse {
    cells: HeatmapCell[];
    dataset_id: string;
    top_k: number;
}

export interface RadarEntry {
    llm_id: string;
    dimension: string;
    avg_value: number | null;
    n: number;
}

export interface RadarResponse {
    entries: RadarEntry[];
}

export interface UpliftItem {
    llm_id: string;
    avg_baseline: number | null;
    avg_galileo: number | null;
    n_pairs: number;
    delta: number | null;
}

export interface UpliftResponse {
    items: UpliftItem[];
}

export interface FailureBreakdownItem {
    llm_id: string;
    failure_type: string;
    count: number;
}

export interface FailuresResponse {
    items: FailureBreakdownItem[];
}

export interface ParetoItem {
    llm_id: string;
    avg_score: number | null;
    avg_latency_ms: number | null;
    avg_cost_usd: number | null;
    n: number;
}

export interface ParetoResponse {
    items: ParetoItem[];
}

export interface ScoreBreakdownItem {
    llm_id: string;
    correctness: number;
    grounding: number;
    calibration: number;
    falsifiable: number;
    deference_penalty: number;
    refusal_penalty: number;
    n: number;
}

export interface ScoreBreakdownResponse {
    items: ScoreBreakdownItem[];
}

export interface HallucinationTrendBucket {
    bucket: string;
    hallucination_rate: number | null;
    n: number;
}

export interface HallucinationTrendSeries {
    llm_id: string;
    buckets: HallucinationTrendBucket[];
}

export interface HallucinationTrendResponse {
    series: HallucinationTrendSeries[];
    window_days: number;
}

export interface CalibrationPoint {
    llm_id: string;
    score_total: number;
    calibration: number;
}

export interface CalibrationResponse {
    points: CalibrationPoint[];
}

export interface CostPerPassItem {
    llm_id: string;
    cost_per_pass: number | null;
    total_cost: number;
    passing_runs: number;
    total_runs: number;
}

export interface CostPerPassResponse {
    items: CostPerPassItem[];
}

export interface DashboardResponse {
    summary: ModelsSummaryResponse;
    trend: TrendResponse;
    distribution: DistributionResponse;
    breakdown: ScoreBreakdownResponse;
    radar: RadarResponse;
}
