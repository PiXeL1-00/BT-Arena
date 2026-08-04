"use client";

import { useCallback, useMemo } from "react";
import { useAvailableKeys, useValidateKeys, useDebateConfig } from "@/lib/queries";
import type { KeyValidationStatus } from "@/lib/types";
import type { ModelRegistryEntry } from "@/lib/api";

type ModelDef = ModelRegistryEntry;

export function useKeyValidation() {
    const { data: availableKeysData } = useAvailableKeys();
    const availableKeys = useMemo(
        () => new Set(availableKeysData?.available_keys || []),
        [availableKeysData],
    );

    const {
        data: validationData,
        refetch: refreshValidation,
        isLoading: validationLoading,
        isError: validationError
    } = useValidateKeys();

    const { data: debateConfig } = useDebateConfig();

    const keyValidation = useMemo(
        () => new Map(Object.entries(validationData || {})),
        [validationData],
    );

    const isModelAvailable = useCallback(
        (model: ModelDef) => {
            if (!availableKeysData) return true;
            return availableKeys.has(model.api_key_env);
        },
        [availableKeys, availableKeysData]
    );

    const getValidationStatus = useCallback(
        (model: ModelDef): KeyValidationStatus | null => {
            const validation = keyValidation.get(model.api_key_env);
            return validation?.status || null;
        },
        [keyValidation]
    );

    const isModelAllowedInMode = useCallback(
        (model: ModelDef): boolean => {
            if (!debateConfig || debateConfig.debug_mode) return true;
            const modelKey = `${model.provider}/${model.model_name}`;
            return debateConfig.allowed_models.includes(modelKey);
        },
        [debateConfig]
    );

    const isModelCapExhausted = useCallback(
        (model: ModelDef): boolean => {
            if (!debateConfig || debateConfig.debug_mode) return false;
            const modelKey = `${model.provider}/${model.model_name}`;
            const used = debateConfig.usage_today[modelKey] || 0;
            return used >= debateConfig.daily_cap;
        },
        [debateConfig]
    );

    const getModelUsageRemaining = useCallback(
        (model: ModelDef): number | null => {
            if (!debateConfig || debateConfig.debug_mode) return null;
            const modelKey = `${model.provider}/${model.model_name}`;
            const used = debateConfig.usage_today[modelKey] || 0;
            return Math.max(0, debateConfig.daily_cap - used);
        },
        [debateConfig]
    );

    const isModelDisabled = useCallback(
        (model: ModelDef): boolean => {
            if (!isModelAvailable(model)) return true;
            if (!isModelAllowedInMode(model)) return true;
            if (isModelCapExhausted(model)) return true;
            const status = getValidationStatus(model);
            return (
                status === "INVALID_KEY" || status === "NO_FUNDS_OR_BUDGET"
            );
        },
        [isModelAvailable, isModelAllowedInMode, isModelCapExhausted, getValidationStatus]
    );

    const getDisabledReason = useCallback(
        (model: ModelDef): string | null => {
            if (!isModelAvailable(model)) return "API key not configured";
            if (!isModelAllowedInMode(model)) return "Not available in production mode";
            if (isModelCapExhausted(model)) {
                const used = debateConfig?.usage_today[`${model.provider}/${model.model_name}`] || 0;
                return `Daily limit reached (${used}/${debateConfig?.daily_cap})`;
            }
            const status = getValidationStatus(model);
            if (status === "INVALID_KEY") return "Invalid API key";
            if (status === "NO_FUNDS_OR_BUDGET") return "No funds or budget";
            return null;
        },
        [isModelAvailable, isModelAllowedInMode, isModelCapExhausted, getValidationStatus, debateConfig]
    );

    return {
        availableKeys,
        keyValidation,
        validationLoading,
        validationError,
        refreshValidation,
        isModelAvailable,
        getValidationStatus,
        isModelDisabled,
        isModelAllowedInMode,
        isModelCapExhausted,
        getModelUsageRemaining,
        getDisabledReason,
        debateConfig,
    };
}
