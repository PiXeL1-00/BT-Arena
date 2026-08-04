import { useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type { ModelRegistryEntry } from "./api";
import { DatasetSchema, DatasetDetailSchema, AvailableKeysResponseSchema } from "./schemas";
import type { RunRequest } from "./types";

// Keys for query caching
export const queryKeys = {
    datasets: ["datasets"] as const,
    dataset: (id: string) => ["dataset", id] as const,
    availableKeys: ["availableKeys"] as const,
    keyValidation: ["keyValidation"] as const,
    debateConfig: ["debateConfig"] as const,
    modelRegistry: ["modelRegistry"] as const,
    run: (id: string) => ["run", id] as const,
    runSummary: (id: string) => ["runSummary", id] as const,
    caseReplay: (runId: string, caseId: string) => ["caseReplay", runId, caseId] as const,
};

// --- Dataset Queries ---

export function useDatasets() {
    return useQuery({
        queryKey: queryKeys.datasets,
        queryFn: () => api.listDatasets(),
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
}

export function useDataset(id: string | null) {
    return useQuery({
        queryKey: queryKeys.dataset(id!),
        queryFn: () => api.getDataset(id!),
        enabled: !!id,
        staleTime: Infinity, // Datasets are static
    });
}

// --- Model/Key Queries ---

export function useAvailableKeys() {
    return useQuery({
        queryKey: queryKeys.availableKeys,
        queryFn: () => api.getAvailableKeys(),
        staleTime: 10 * 1000, // 10 seconds
    });
}

export function useValidateKeys(force = false) {
    return useQuery({
        queryKey: [...queryKeys.keyValidation, force],
        queryFn: () => api.validateKeys(force),
        staleTime: force ? 0 : 5 * 60 * 1000,
        refetchOnWindowFocus: false,
    });
}

export function useDebateConfig() {
    return useQuery({
        queryKey: queryKeys.debateConfig,
        queryFn: () => api.getDebateConfig(),
        staleTime: 30 * 1000,
    });
}

export function useModelRegistry() {
    return useQuery<ModelRegistryEntry[]>({
        queryKey: queryKeys.modelRegistry,
        queryFn: async () => {
            const data = await api.getModelRegistry();
            return data.models;
        },
        staleTime: 5 * 60 * 1000, // 5 minutes — models rarely change at runtime
    });
}

// --- Run Queries ---

export function useCreateRun() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: RunRequest) => api.createRun(data),
        onSuccess: (data) => {
            // Invalidate runs list if we had one
            // queryClient.invalidateQueries({ queryKey: ['runs'] });
        },
    });
}

export function useCaseReplay(runId: string, caseId: string) {
    return useQuery({
        queryKey: queryKeys.caseReplay(runId, caseId),
        queryFn: () => api.getCaseReplay(runId, caseId),
        enabled: !!runId && !!caseId,
        // Replay data is immutable once written
        staleTime: Infinity,
    });
}

export function useRunDetails(runId: string | null) {
    const queryClient = useQueryClient();
    const prevStatus = useRef<string | undefined>(undefined);

    const {
        data: run,
        isLoading: runLoading,
        error: runError,
        isError: isRunError
    } = useQuery({
        queryKey: queryKeys.run(runId!),
        queryFn: () => (runId ? api.getRun(runId) : null),
        enabled: !!runId,
        refetchInterval: (query) => {
            const data = query.state.data;
            return data && data.status !== "COMPLETED" && data.status !== "FAILED" ? 3000 : false;
        },
    });

    const {
        data: summary,
        isLoading: summaryLoading,
        error: summaryError,
        isError: isSummaryError
    } = useQuery({
        queryKey: queryKeys.runSummary(runId!),
        queryFn: () => (runId ? api.getRunSummary(runId) : null),
        enabled: !!runId,
        refetchInterval: (query) => {
            if (!run) return 3000;
            return run.status !== "COMPLETED" && run.status !== "FAILED" ? 3000 : false;
        },
    });

    useEffect(() => {
        if (!runId || !run?.status) return;
        const wasActive = prevStatus.current && prevStatus.current !== "COMPLETED" && prevStatus.current !== "FAILED";
        const nowDone = run.status === "COMPLETED" || run.status === "FAILED";
        prevStatus.current = run.status;
        if (wasActive && nowDone) {
            queryClient.invalidateQueries({ queryKey: queryKeys.runSummary(runId) });
        }
    }, [run?.status, runId, queryClient]);

    return {
        run,
        summary,
        runLoading,
        summaryLoading,
        loading: runLoading || summaryLoading,
        error: runError || summaryError,
        isError: isRunError || isSummaryError
    };
}
