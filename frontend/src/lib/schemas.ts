import { z } from "zod";

// Shared schemas mirroring backend types

export const DatasetSchema = z.object({
    id: z.string(),
    version: z.string(),
    description: z.string(),
    case_count: z.number(),
});

export const EvidenceSchema = z.object({
    eid: z.string(),
    summary: z.string(),
    source: z.string(),
    date: z.string(),
});

export const DatasetCaseSchema = z.object({
    case_id: z.string(),
    topic: z.string(),
    claim: z.string(),
    pressure_score: z.number(),
    label: z.enum(["SUPPORTED", "REFUTED", "INSUFFICIENT"]),
    evidence_packets: z.array(EvidenceSchema),
});

export const DatasetDetailSchema = z.object({
    id: z.string(),
    version: z.string(),
    description: z.string(),
    meta: z.record(z.string(), z.unknown()),
    cases: z.array(DatasetCaseSchema),
});

export const ModelConfigSchema = z.object({
    provider: z.string(),
    model_name: z.string(),
});

export const RunInfoSchema = z.object({
    run_id: z.string(),
    dataset_id: z.string(),
    case_id: z.string(),
    status: z.enum(["PENDING", "RUNNING", "COMPLETED", "FAILED"]),
    models: z.array(ModelConfigSchema),
    created_at: z.string(),
    finished_at: z.string().nullable(),
    total_llm_cost: z.number().optional(),
    debug_mode: z.boolean().optional(),
});

export const CaseResultSchema = z.object({
    case_id: z.string(),
    model_key: z.string(),
    verdict: z.enum(["SUPPORTED", "REFUTED", "INSUFFICIENT"]),
    label: z.enum(["SUPPORTED", "REFUTED", "INSUFFICIENT"]),
    score: z.number(),
    passed: z.boolean(),
    confidence: z.number(),
    latency_ms: z.number(),
    critical_fail_reason: z.string().nullable(),
});

export const KeyValidationResultSchema = z.object({
    status: z.enum([
        "VALID",
        "INVALID_KEY",
        "NO_FUNDS_OR_BUDGET",
        "RATE_LIMIT",
        "PERMISSION_OR_REGION",
        "PROVIDER_OUTAGE",
        "TIMEOUT",
        "UNKNOWN_ERROR",
    ]),
    provider: z.string(),
    api_key_env: z.string(),
    error_message: z.string().nullable(),
    request_id: z.string().nullable(),
    http_status: z.number().nullable(),
    validated_at: z.string().nullable(),
});

export const AvailableKeysResponseSchema = z.object({
    available_keys: z.array(z.string()),
    validation: z.record(z.string(), KeyValidationResultSchema).optional(),
    validation_error: z.string().optional(),
});

export const ModelMetricsSchema = z.object({
    model_key: z.string(),
    total_cases: z.number(),
    passed_cases: z.number(),
    failed_cases: z.number(),
    critical_fails: z.number(),
    pass_rate: z.number(),
    avg_score: z.number(),
    avg_latency_ms: z.number(),
    total_cost: z.number(),
    high_pressure_pass_rate: z.number(),
    model_passes_eval: z.boolean(),
});

export const RunSummarySchema = z.object({
    run_id: z.string(),
    status: z.enum(["PENDING", "RUNNING", "COMPLETED", "FAILED"]),
    total_cases: z.number(),
    models: z.array(ModelMetricsSchema),
    total_llm_cost: z.number().optional(),
    debug_mode: z.boolean().optional(),
});
