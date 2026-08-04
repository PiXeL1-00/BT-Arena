/* Typed API client for the FastAPI backend. */

import { API_BASE, SSE_BASE, ADMIN_API_KEY } from "./constants";
import type {
  Dataset,
  DatasetDetail,
  RunInfo,
  RunSummary,
  CaseResult,
  RunRequest,
  AvailableKeysResponse,
  KeyValidationResult,
} from "./types";
import {
  RunInfoSchema,
  RunSummarySchema
} from "./schemas";
import type { CaseReplayData } from "./eventTypes";

export interface DebateConfig {
  debug_mode: boolean;
  allowed_models: string[];
  daily_cap: number;
  usage_today: Record<string, number>;
}

export interface ModelRegistryEntry {
  id: string;
  provider: string;
  model_name: string;
  label: string;
  api_key_env: string;
}

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  async listDatasets(): Promise<Dataset[]> {
    return fetchJSON<Dataset[]>("/datasets");
  },

  async getDataset(id: string) {
    return fetchJSON<DatasetDetail>(`/datasets/${id}`);
  },

  async createRun(body: RunRequest): Promise<{ run_id: string }> {
    const res = await fetch(`${API_BASE}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
    return res.json();
  },

  async getRun(runId: string): Promise<RunInfo> {
    const data = await fetchJSON<unknown>(`/runs/${runId}`);
    return RunInfoSchema.parseAsync(data);
  },

  async getRunSummary(runId: string): Promise<RunSummary> {
    const data = await fetchJSON<unknown>(`/runs/${runId}/summary`);
    return RunSummarySchema.parseAsync(data);
  },

  async getRunCases(
    runId: string,
    params?: { model?: string; status?: string; skip?: number; limit?: number }
  ): Promise<{ total: number; cases: CaseResult[] }> {
    const qs = new URLSearchParams();
    if (params?.model) qs.set("model", params.model);
    if (params?.status) qs.set("status", params.status);
    if (params?.skip) qs.set("skip", String(params.skip));
    if (params?.limit) qs.set("limit", String(params.limit));
    return fetchJSON(`/runs/${runId}/cases?${qs}`);
  },

  async getCaseReplay(runId: string, caseId: string) {
    return fetchJSON<CaseReplayData>(`/runs/${runId}/cases/${caseId}`);
  },

  async getRunMessages(runId: string) {
    return fetchJSON<Array<{
      role: string;
      model_key: string;
      content: string;
      phase: string | null;
      round: number | null;
      created_at: string;
    }>>(`/runs/${runId}/messages`);
  },

  async getAvailableKeys(): Promise<{ available_keys: string[] }> {
    return fetchJSON<{ available_keys: string[] }>("/models/available-keys");
  },

  async validateKeys(force?: boolean): Promise<Record<string, KeyValidationResult>> {
    try {
      const qs = new URLSearchParams();
      qs.set("validate", "true");
      if (force) {
        qs.set("force", "true");
      }
      const res = await fetch(`${API_BASE}/models/available-keys?${qs}`, {
        headers: ADMIN_API_KEY ? { "X-Admin-Key": ADMIN_API_KEY } : {},
      });
      if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
      const response = (await res.json()) as AvailableKeysResponse;
      return response.validation || {};
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      if (!errorMessage.includes("429") && !errorMessage.includes("Rate limit")) {
        console.error("Failed to validate keys:", err);
      }
      return {};
    }
  },

  async getDebateConfig(): Promise<DebateConfig> {
    return fetchJSON<DebateConfig>("/models/debate-config");
  },

  async getModelRegistry(): Promise<{ models: ModelRegistryEntry[] }> {
    return fetchJSON<{ models: ModelRegistryEntry[] }>("/models/registry");
  },

  eventsUrl(runId: string): string {
    return `${SSE_BASE}/runs/${runId}/events`;
  },
};
