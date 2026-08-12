import { AlertTriangle, Info, RefreshCw } from "lucide-react";
import type { KeyValidationResult, KeyValidationStatus } from "@/lib/types";
import type { ModelRegistryEntry } from "@/lib/api";
import { RefObject } from "react";

interface Props {
    models: ModelRegistryEntry[];
    selectedModel: string;
    onSelectModel: (model: string) => void;
    isModelDisabled: (model: ModelRegistryEntry) => boolean;
    getValidationStatus: (model: ModelRegistryEntry) => KeyValidationStatus | null;
    getDisabledReason?: (model: ModelRegistryEntry) => string | null;
    getModelUsageRemaining?: (model: ModelRegistryEntry) => number | null;
    validationLoading: boolean;
    onRefreshValidation: () => void;
    keyValidation: Map<string, KeyValidationResult>;
    highlighted?: boolean;
    containerRef?: RefObject<HTMLDivElement>;
}

export function ModelSelector({
    models,
    selectedModel,
    onSelectModel,
    isModelDisabled,
    getValidationStatus,
    getDisabledReason,
    getModelUsageRemaining,
    validationLoading,
    onRefreshValidation,
    keyValidation,
    highlighted,
    containerRef
}: Props) {

    return (
        <div
            ref={containerRef}
            className={`glass-panel rounded-3xl p-6 shadow-lg transition-all duration-700 ${highlighted
                ? 'border-[#412AD1]/60 bg-[#412AD1]/10 shadow-[0_0_30px_rgba(65,42,209,0.25)] ring-2 ring-[#412AD1]/30'
                : ''
                }`}
        >
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xs font-semibold text-[#412AD1] tracking-widest uppercase flex items-center gap-2">
                    Inference Engine
                    <div className="relative group/info">
                        <Info className="w-3 h-3 text-[#292524]/30 cursor-help" />
                        <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-48 p-2 bg-[#FFFFFF] border border-[#292524]/10 rounded-lg text-[10px] text-[#292524]/70 pointer-events-none opacity-0 group-hover/info:opacity-100 transition-opacity z-50 shadow-lg">
                            Select the LLM that will power the debate agents.
                        </div>
                    </div>
                </h2>

                <button
                    onClick={onRefreshValidation}
                    disabled={validationLoading}
                    className="p-1.5 rounded-lg hover:bg-[#412AD1]/10 text-[#292524]/40 hover:text-[#412AD1] transition-colors disabled:opacity-50"
                    title="Refresh API key validation"
                >
                    <RefreshCw className={`w-3 h-3 ${validationLoading ? "animate-spin" : ""}`} />
                </button>
            </div>

            <div className="relative">
                <select
                    value={selectedModel}
                    onChange={(e) => onSelectModel(e.target.value)}
                    className="w-full appearance-none bg-background/50 border border-primary/20 rounded-xl px-5 py-4 text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all font-medium"
                >
                    <option value="" className="bg-background text-muted-foreground">-- Select an Inference Engine --</option>
                    {models.map((model) => {
                        const disabled = isModelDisabled(model);
                        const remaining = getModelUsageRemaining?.(model);
                        const suffix = remaining !== null && remaining !== undefined
                            ? ` [${remaining} left today]`
                            : "";
                        return (
                            <option
                                key={model.id}
                                value={model.id}
                                disabled={disabled}
                                className="bg-background text-foreground"
                            >
                                {model.label} ({model.provider}){suffix}
                            </option>
                        );
                    })}
                </select>
                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground">▼</div>
            </div>

            {selectedModel && (() => {
                const model = models.find(m => m.id === selectedModel);
                if (!model) return null;

                const reason = getDisabledReason?.(model);
                if (reason) {
                    return (
                        <div className="mt-3 text-[10px] text-[#B50BBB] bg-[#B50BBB]/10 p-2 rounded border border-[#B50BBB]/20 flex items-center gap-2">
                            <AlertTriangle className="w-3 h-3" />
                            {reason}
                        </div>
                    );
                }

                const status = getValidationStatus(model);
                if (status && status !== "VALID") {
                    const result = keyValidation.get(model.api_key_env);
                    const errorText = result?.error_message || status;
                    return (
                        <div className="mt-3 text-[10px] text-[#B50BBB] bg-[#B50BBB]/10 p-2 rounded border border-[#B50BBB]/20 flex items-center gap-2">
                            <AlertTriangle className="w-3 h-3" />
                            {errorText}
                        </div>
                    );
                }
                return null;
            })()}
        </div>
    );
}
