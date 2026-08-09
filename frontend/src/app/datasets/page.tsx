"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import CopernicanSystem from "@/components/CopernicanSystem";
import { ModelSelector } from "@/components/ModelSelector";
import type {
    Dataset,
    DatasetCase,
    KeyValidationResult,
    KeyValidationStatus
} from "@/lib/types";
import { useDatasets, useDataset, useModelRegistry } from "@/lib/queries";
import { GlassCard } from "@/components/ui/GlassCard";
import { useKeyValidation } from "@/hooks/useKeyValidation";

export default function DatasetsPage() {
    const router = useRouter();
    const { data: datasets = [], isLoading: datasetsLoading } = useDatasets();
    const [selected, setSelected] = useState<string>("");
    const [navigating, setNavigating] = useState(false);

    const { data: datasetDetail, isLoading: casesLoading } = useDataset(selected || null);
    const cases = datasetDetail?.cases || [];

    const { data: models = [] } = useModelRegistry();

    const [selectedCaseId, setSelectedCaseId] = useState<string>("");
    const [selectedModel, setSelectedModel] = useState<string>("");
    const [launching, setLaunching] = useState(false);
    const [error, setError] = useState<string>("");

    const [highlightCaseSelector, setHighlightCaseSelector] = useState(false);
    const caseSelectorRef = useRef<HTMLDivElement>(null);

    const [highlightModelSelector, setHighlightModelSelector] = useState(false);
    const modelSelectorRef = useRef<HTMLDivElement>(null);

    const {
        isModelDisabled,
        getValidationStatus,
        getDisabledReason,
        getModelUsageRemaining,
        keyValidation,
        validationLoading,
        refreshValidation,
        filterAvailableModels,
    } = useKeyValidation();

    // Only models whose API key is present and real — missing-key models are hidden entirely
    const availableModels = filterAvailableModels(models);

    const handleSelectDataset = useCallback((dsId: string) => {
        setSelected(dsId);
        setSelectedCaseId("");
        setSelectedModel("");
        setHighlightCaseSelector(false);
        setHighlightModelSelector(false);
    }, []);



    // Scroll to and highlight Target Case when dataset is selected and cases are loaded
    useEffect(() => {
        if (selected && caseSelectorRef.current && !casesLoading && cases.length > 0) {
            setTimeout(() => {
                caseSelectorRef.current?.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center',
                    inline: 'nearest'
                });
                setHighlightCaseSelector(true);
                setTimeout(() => setHighlightCaseSelector(false), 3000);
            }, 300);
        }
    }, [selected, casesLoading, cases.length]);

    // Scroll to and highlight Inference Engine when Target Case is selected
    useEffect(() => {
        if (selectedCaseId && modelSelectorRef.current) {
            setTimeout(() => {
                modelSelectorRef.current?.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center',
                    inline: 'nearest'
                });
                setHighlightModelSelector(true);
                setTimeout(() => setHighlightModelSelector(false), 3000);
            }, 300);
        }
    }, [selectedCaseId]);



    const handleLaunch = async () => {
        if (!selected || !selectedCaseId || !selectedModel) return;
        setLaunching(true);
        setError("");
        try {
            const m = availableModels.find(
                (am) => am.id === selectedModel
            )!;
            const modelConfigs = [
                { provider: m.provider, model_name: m.model_name, api_key_env: m.api_key_env },
            ];
            const resp = await api.createRun({
                dataset_id: selected,
                case_id: selectedCaseId,
                models: modelConfigs,
                mode: "debate",
            });
            if (resp.run_id) {
                setNavigating(true);
                router.push(`/run/${resp.run_id}`);
            } else {
                setError("No run_id in response: " + JSON.stringify(resp));
            }
        } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            console.error(err);
            setError(msg);
        } finally {
            setLaunching(false);
        }
    };

    if (navigating) {
        return (
            <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-slate-950">
                <div className="relative mb-8">
                    <div className="w-20 h-20 rounded-full border-2 border-cyan-500/20" />
                    <div className="absolute inset-0 w-20 h-20 rounded-full border-2 border-transparent border-t-cyan-400 animate-spin" />
                    <div className="absolute inset-3 w-14 h-14 rounded-full border-2 border-transparent border-b-teal-400 animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
                </div>
                <h2 className="text-2xl font-light text-white mb-2 tracking-wide">Preparing AI Evaluation</h2>
                <p className="text-sm text-cyan-400/80 animate-pulse tracking-widest uppercase">Loading Subnet Comparison...</p>
            </div>
        );
    }

    return (
        <div className="relative min-h-screen w-full overflow-hidden flex flex-col items-center justify-start lg:justify-center p-4 pt-16 sm:p-8 sm:pt-20">
            {/* Background System */}
            <CopernicanSystem />

            {/* Main Content Container */}
            <div className="relative z-10 w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

                {/* Header / Intro - Left Side */}
                <div className="lg:col-span-4 flex flex-col justify-center space-y-6 lg:sticky lg:top-24">
                    <h1 className="text-3xl sm:text-5xl lg:text-6xl text-white font-display font-bold leading-tight bg-gradient-to-r from-cyan-200 via-teal-200 to-white bg-clip-text text-transparent drop-shadow-[0_0_10px_rgba(34,211,238,0.15)]">
                        Bittensor <span className="hidden sm:inline"><br /></span>Arena
                    </h1>
                    <p className="text-lg text-slate-300 font-light leading-relaxed backdrop-blur-sm bg-slate-900/30 p-4 rounded-xl border border-white/5">
                        Select a subnet category to begin. Each category contains competing Bittensor subnets that are evaluated by AI models using a consistent methodology to determine the strongest projects within that domain.
                    </p>

                    {/* Case Selector - Relocated */}
                    {/* Case Selector - With Auto-Scroll and Highlight */}
                    {selected && (
                        <div ref={caseSelectorRef}>
                            <GlassCard
                                size="lg"
                                className={`space-y-3 animate-in fade-in slide-in-from-left-4 duration-700 transition-all ${highlightCaseSelector
                                    ? 'border-cyan-400/60 bg-cyan-500/10 shadow-[0_0_30px_rgba(34,211,238,0.4)] ring-2 ring-cyan-400/30'
                                    : ''
                                    }`}
                            >
                                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-widest pl-1">Subnet</label>
                                {casesLoading ? (
                                    <div className="h-12 w-full rounded-xl bg-muted/20 animate-pulse" />
                                ) : (
                                    <div className="relative">
                                        <select
                                            value={selectedCaseId}
                                            onChange={(e) => setSelectedCaseId(e.target.value)}
                                            className="w-full appearance-none bg-background/50 border border-primary/20 rounded-xl px-5 py-4 text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
                                        >
                                            <option value="" className="bg-background">-- Select a subnet --</option>
                                            {cases.map((c: DatasetCase) => (
                                                <option key={c.case_id} value={c.case_id} className="bg-background">
                                                    {c.case_id}
                                                </option>
                                            ))}
                                        </select>
                                        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground">▼</div>
                                    </div>
                                )}
                            </GlassCard>
                        </div>
                    )}
                </div>

                {/* Interactive Panel - Right Side */}
                <div className="lg:col-span-8 flex flex-col gap-6">

                    {/* Dataset Selection - Horizontal Scroll or Grid */}
                    <div className="glass-panel border-white/10 bg-slate-950/40 backdrop-blur-md rounded-3xl p-6 shadow-2xl">
                        <h2 className="text-xs font-semibold text-cyan-400 mb-4 tracking-widest uppercase">Subnet Categories</h2>
                        {datasetsLoading ? (
                            <div className="flex flex-col items-center justify-center py-16 gap-4">
                                <div className="relative w-12 h-12">
                                    <div className="absolute inset-0 rounded-full border-2 border-cyan-500/20" />
                                    <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-cyan-400 animate-spin" />
                                </div>
                                <p className="text-sm text-slate-400 animate-pulse">Loading subnet categories…</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {datasets.map((ds: Dataset) => (
                                    <button
                                        key={ds.id}
                                        onClick={() => handleSelectDataset(ds.id)}
                                        className={`group relative overflow-hidden rounded-2xl p-5 text-left transition-all duration-300 border ${selected === ds.id
                                            ? "bg-cyan-500/10 border-cyan-500/50 shadow-[0_0_20px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/30"
                                            : "bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/10"
                                            }`}
                                    >
                                        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/0 via-cyan-500/0 to-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                                        <h3 className={`text-lg font-medium transition-colors ${selected === ds.id ? "text-cyan-200" : "text-white"}`}>{ds.id}</h3>
                                        <p className="text-sm text-slate-400 mt-2 line-clamp-2 leading-relaxed">{ds.description}</p>
                                        <div className="flex items-center gap-2 mt-4 text-xs text-white/30">
                                            <span className="px-2 py-1 rounded-full bg-white/5">{ds.case_count} orbits</span>
                                            <span>v{ds.version}</span>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Model Selector */}
                    {selected && selectedCaseId && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <ModelSelector
                                models={availableModels}
                                selectedModel={selectedModel}
                                onSelectModel={setSelectedModel}
                                isModelDisabled={isModelDisabled}
                                getValidationStatus={getValidationStatus}
                                getDisabledReason={getDisabledReason}
                                getModelUsageRemaining={getModelUsageRemaining}
                                validationLoading={validationLoading}
                                onRefreshValidation={refreshValidation}
                                keyValidation={keyValidation}
                                highlighted={highlightModelSelector}
                                containerRef={modelSelectorRef}
                            />

                            {/* Launch Button */}
                            <div className="pt-4 flex flex-col gap-4">
                                <button
                                    onClick={handleLaunch}
                                    disabled={launching || !selectedModel}
                                    className="group relative w-full h-14 overflow-hidden rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 disabled:from-slate-800 disabled:to-slate-900 transition-all duration-300 shadow-lg hover:shadow-cyan-500/25"
                                >
                                    <div className="absolute inset-0 bg-white/20 group-hover:translate-x-full transition-transform duration-700 ease-out skew-x-12 -translate-x-[150%]" />
                                    <span className="relative flex items-center justify-center gap-2 font-medium text-lg tracking-wide text-white">
                                        {launching ? (
                                            <>
                                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                                Initiating Sequence...
                                            </>
                                        ) : (
                                            "Launch Analysis"
                                        )}
                                    </span>
                                </button>

                                {error && (
                                    <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-sm text-center animate-in fade-in slide-in-from-top-2">
                                        {error}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
