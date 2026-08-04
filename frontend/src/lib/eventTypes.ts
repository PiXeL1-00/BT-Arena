// SSE Event types
import type { Verdict } from "./types";
export type SSEPayload =
    | AgentMessagePayload
    | CaseScoredPayload
    | MetricsUpdatePayload
    | QuotaExhaustedPayload;

export interface AgentMessagePayload {
    event_type: 'agent_message';
    role: string;
    model_key: string;
    content: string;
    phase?: string;
    round?: number;
}

export interface CaseScoredPayload {
    event_type: 'case_scored';
    case_id: string;
    model_key: string;
    verdict: Verdict;
    score: number;
    passed: boolean;
}

export interface MetricsUpdatePayload {
    event_type: 'metrics_update';
    completed: number;
    total: number;
}

export interface QuotaExhaustedPayload {
    event_type: 'quota_exhausted';
    model_key: string;
    provider: string;
    message: string;
}

export interface SSEEvent {
    event_type: 'agent_message' | 'case_scored' | 'metrics_update' | 'quota_exhausted';
    payload: SSEPayload;
}

// Case Replay data type
export interface CaseReplayData {
    case_id: string;
    messages: Array<{
        role: string;
        model_key: string;
        content: string;
        created_at: string;
    }>;
    results: Array<{
        model_key: string;
        verdict: Verdict;
        label: string;
        score: number;
        passed: boolean;
        judge_json: Record<string, unknown>;
        critical_fail_reason: string | null;
    }>;
}
