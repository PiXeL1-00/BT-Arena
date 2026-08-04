"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import dynamic from "next/dynamic";
import {
  Swords, Activity, Heart, Zap, Brain, Shield,
  Target, AlertTriangle, CheckCircle, Clock
} from "lucide-react";
import { useSSE } from "@/hooks/useSSE";
import { useRunDetails } from "@/lib/queries";
import { api } from "@/lib/api";
import type { SSEEvent } from "@/lib/eventTypes";
import { Leaderboard } from "@/components/Leaderboard";
import { EvidencePanel } from "@/components/EvidencePanel";
import { GlassCard } from "@/components/ui/GlassCard";
import { LiveTranscript } from "@/components/LiveTranscript";
import { PressureScatter } from "@/components/PressureScatter";
import { ConfusionMatrix } from "@/components/ConfusionMatrix";
import { CalibrationChart } from "@/components/CalibrationChart";
import { FailGallery } from "@/components/FailGallery";
import type { AgentMessage, CaseResult, DatasetDetail, Evidence } from "@/lib/types";
import { useNavLock } from "@/hooks/useNavLock";

const Earth3D = dynamic(() => import("@/components/Earth3D"), { ssr: false });

export default function RunDashboard() {
  const { runId } = useParams<{ runId: string }>();
  const { run, summary, runLoading, error, isError } = useRunDetails(runId);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [scores, setScores] = useState<CaseResult[]>([]);
  const [progress, setProgress] = useState({ completed: 0, total: 0 });
  const [quotaAlert, setQuotaAlert] = useState<string | null>(null);
  const [datasetInfo, setDatasetInfo] = useState<{ datasetId: string; caseTopic: string; claim: string; evidences: Evidence[] } | null>(null);
  const [historicalMessagesLoaded, setHistoricalMessagesLoaded] = useState(false);
  const { lock, unlock } = useNavLock();
  const hasLockedRef = useRef(false);

  const handleEvent = useCallback((event: SSEEvent) => {
    switch (event.event_type) {
      case "agent_message": {
        const p = event.payload as import("@/lib/eventTypes").AgentMessagePayload;
        setMessages((prev) => [
          ...prev,
          {
            role: p.role,
            model_key: p.model_key,
            content: p.content,
            phase: p.phase,
            round: p.round,
          },
        ]);
        break;
      }
      case "case_scored": {
        const p = event.payload as import("@/lib/eventTypes").CaseScoredPayload;
        setScores((prev) => [
          ...prev,
          {
            case_id: p.case_id,
            model_key: p.model_key,
            verdict: p.verdict,
            label: "INSUFFICIENT",
            score: p.score,
            passed: p.passed,
            confidence: 0,
            latency_ms: 0,
            critical_fail_reason: null,
          },
        ]);
        break;
      }
      case "metrics_update": {
        const p = event.payload as import("@/lib/eventTypes").MetricsUpdatePayload;
        setProgress({ completed: p.completed, total: p.total });
        break;
      }
      case "quota_exhausted": {
        const p = event.payload as import("@/lib/eventTypes").QuotaExhaustedPayload;
        setQuotaAlert(p.message);
        setMessages((prev) => [
          ...prev,
          {
            role: "system",
            model_key: p.model_key,
            content: p.message,
          },
        ]);
        break;
      }
    }
  }, []);

  const sseStatus = useSSE(runId ? api.eventsUrl(runId) : null, handleEvent);

  // Lock nav while debate is in progress, unlock on completion/error
  useEffect(() => {
    const isActive = run?.status === "RUNNING" || run?.status === "PENDING";
    const isDone = run?.status === "COMPLETED" || run?.status === "FAILED";
    const sseStuck = sseStatus === "ERROR";

    if (isActive && !isDone && !sseStuck) {
      lock();
      hasLockedRef.current = true;
    } else if (hasLockedRef.current) {
      unlock();
      hasLockedRef.current = false;
    }
  }, [run?.status, sseStatus, lock, unlock]);

  // Cleanup: unlock if user navigates away mid-debate
  useEffect(() => {
    return () => {
      if (hasLockedRef.current) {
        unlock();
        hasLockedRef.current = false;
      }
    };
  }, [unlock]);

  // Reset state when runId changes
  useEffect(() => {
    setMessages([]);
    setScores([]);
    setProgress({ completed: 0, total: 0 });
    setHistoricalMessagesLoaded(false);
  }, [runId]);
  // ... (skipping lines 81-283 for brevity in this instruction, but tool handles chunks)

  // Poll for messages only when SSE is not connected (fallback)
  useEffect(() => {
    if (!runId || run?.status === "COMPLETED" || run?.status === "FAILED") return;
    if (sseStatus === "OPEN") return;

    const interval = setInterval(async () => {
      try {
        const msgs = await api.getRunMessages(runId);
        setMessages((prev) => {
          if (msgs.length === prev.length) return prev;
          return msgs.map((m) => ({
            role: m.role,
            model_key: m.model_key,
            content: m.content,
            phase: m.phase ?? undefined,
            round: m.round ?? undefined,
          }));
        });
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [runId, run?.status, sseStatus]);

  // Load historical messages for completed runs
  useEffect(() => {
    if (!runId || !run || historicalMessagesLoaded) return;

    // If we already have messages, don't load history
    if (messages.length > 0) {
      setHistoricalMessagesLoaded(true);
      return;
    }



    // If run is completed and we have no messages, load historical data once
    if (run.status === "COMPLETED") {
      const loadHistoricalData = async () => {
        try {
          const [historicalMessages, casesResponse] = await Promise.all([
            api.getRunMessages(runId),
            api.getRunCases(runId, { limit: 200 }),
          ]);
          setMessages(
            historicalMessages.map((m) => ({
              role: m.role,
              model_key: m.model_key,
              content: m.content,
              phase: m.phase ?? undefined,
              round: m.round ?? undefined,
            }))
          );
          if (casesResponse.cases.length > 0) {
            setScores(casesResponse.cases);
          }
        } catch (err) {
          console.error("Failed to load historical data:", err);
        } finally {
          setHistoricalMessagesLoaded(true);
        }
      };
      loadHistoricalData();
    }
  }, [runId, run?.status, historicalMessagesLoaded, messages.length]);

  // Fetch dataset and case information when run data is available
  useEffect(() => {
    if (!run?.dataset_id || !run?.case_id) return;

    const fetchDatasetInfo = async () => {
      try {
        const dataset: DatasetDetail = await api.getDataset(run.dataset_id);
        const caseData = dataset.cases.find((c) => c.case_id === run.case_id);
        if (caseData) {
          setDatasetInfo({
            datasetId: dataset.id,
            caseTopic: caseData.topic,
            claim: caseData.claim,
            evidences: caseData.evidence_packets ?? [],
          });
        }
      } catch (err) {
        console.error("Failed to fetch dataset info:", err);
      }
    };

    fetchDatasetInfo();
  }, [run?.dataset_id, run?.case_id]);

  if (isError || (!runLoading && !run)) {
    return (
      <div className="flex items-center justify-center min-h-screen w-full bg-background relative overflow-hidden">
        <div className="fixed inset-0 z-0 opacity-20 pointer-events-none"><Earth3D /></div>
        <div className="relative z-10 p-8 glass-panel border-red-500/30 bg-red-950/20 max-w-md text-center backdrop-blur-md rounded-3xl">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-red-400 mb-2">Failed to Load Run</h2>
          <p className="text-white/60 mb-6 font-light">{(error as Error)?.message || "Run data could not be retrieved. It may not exist or the service is unavailable."}</p>
          <a href="/datasets" className="inline-block px-6 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded-lg transition-colors border border-red-500/20">
            Return to Datasets
          </a>
        </div>
      </div>
    );
  }

  if (runLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen w-full bg-background relative overflow-hidden">
        <div className="absolute inset-0 z-0 opacity-20">
          <Earth3D />
        </div>
        <div className="glass-panel rounded-3xl p-12 text-center z-10 animate-pulse">
          <div className="h-12 w-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-white/60 tracking-wider font-light">INITIALIZING RUN ENVIRONMENT...</p>
        </div>
      </div>
    );
  }

  const pct =
    progress.total > 0
      ? Math.round((progress.completed / progress.total) * 100)
      : 0;

  return (
    <div className="relative min-h-screen w-full bg-background overflow-hidden flex flex-col">
      {/* Ambient Background */}
      <div className="fixed inset-0 z-0 opacity-40 pointer-events-none">
        <Earth3D />
      </div>
      <div className="fixed inset-0 z-0 bg-gradient-to-t from-background via-transparent to-transparent pointer-events-none" />

      <div className="relative z-10 flex-1 flex flex-col p-3 sm:p-6 overflow-y-auto w-full h-full">

        {/* Header Section */}
        <div className="mb-4 sm:mb-8 mt-10 sm:mt-12 w-full max-w-7xl mx-auto">
          <GlassCard size="lg">

            {/* Title Area */}
            <div className="flex items-start gap-3 sm:gap-4 z-10">
              <div className="p-2 sm:p-3 rounded-xl bg-primary/10 border border-primary/20 text-primary shadow-[0_0_15px_rgba(59,130,246,0.2)]">
                <Swords className="h-5 w-5 sm:h-8 sm:w-8 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-xs font-bold tracking-[0.2em] text-cyan-400 uppercase">Active Debate Protocol</span>
                  <div className="h-px w-12 bg-gradient-to-l from-cyan-400 to-transparent"></div>
                </div>
                <h1 className="text-xl sm:text-3xl font-light text-white tracking-tight">
                  {datasetInfo ? (
                    <span className="flex items-baseline gap-2 flex-wrap">
                      <span className="font-semibold text-white">{datasetInfo.datasetId}</span>
                      <span className="text-white/40 font-thin">/</span>
                      <span className="text-cyan-300">{datasetInfo.caseTopic}</span>
                    </span>
                  ) : (
                    <span className="text-white/80">
                      Run <span className="text-cyan-300 font-mono">{runId?.slice(0, 8)}</span>
                    </span>
                  )}
                </h1>
              </div>
            </div>

            {/* Stats / Status Area */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-6 z-10 w-full">
              {datasetInfo?.claim && (
                <div className="hidden lg:block max-w-md">
                  <div className="text-xs text-white/40 mb-1 uppercase tracking-wider">Target Claim</div>
                  <div className="text-sm text-green-300/90 font-mono border-l-2 border-green-500/30 pl-3 py-1 bg-green-500/5">
                    "{datasetInfo.claim.length > 80 ? datasetInfo.claim.substring(0, 80) + '...' : datasetInfo.claim}"
                  </div>
                </div>
              )}

              <div className="flex flex-col items-end gap-2 ml-auto">
                <div className={`px-4 py-1.5 rounded-full border ${run?.status === "COMPLETED"
                  ? "bg-green-500/10 border-green-500/30 text-green-400"
                  : run?.status === "FAILED"
                    ? "bg-red-500/10 border-red-500/30 text-red-400"
                    : "bg-yellow-500/10 border-yellow-500/30 text-yellow-400 animate-pulse"
                  } text-sm font-medium flex items-center gap-2`}>
                  {run?.status === "COMPLETED" && <CheckCircle className="w-4 h-4" />}
                  {run?.status === "FAILED" && <AlertTriangle className="w-4 h-4" />}
                  {run?.status !== "COMPLETED" && run?.status !== "FAILED" && <Activity className="w-4 h-4" />}
                  {run?.status || "PENDING"}
                </div>

                {progress.total > 0 && (
                  <div className="flex flex-col items-end w-40">
                    <div className="text-xs text-white/50 mb-1 flex justify-between w-full">
                      <span>Progress</span>
                      <span>{Math.round((progress.completed / progress.total) * 100)}%</span>
                    </div>
                    <div className="w-full bg-white/10 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-cyan-400 to-blue-500 h-full rounded-full transition-all duration-300 shadow-[0_0_10px_rgba(34,211,238,0.5)]"
                        style={{ width: `${(progress.completed / progress.total) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Debug Info */}
        {(run?.debug_mode ?? summary?.debug_mode ?? false) && (
          <div className="max-w-7xl mx-auto w-full mb-6">
            <div className="glass-panel rounded-xl p-4 border border-yellow-500/20 bg-yellow-500/5">
              <h2 className="text-xs font-bold text-yellow-500/80 mb-2 uppercase tracking-widest flex items-center gap-2">
                <Shield className="w-3 h-3" /> Debug Environment Active
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 text-xs font-mono">
                <div className="p-2 bg-black/20 rounded">
                  <span className="text-white/40 block mb-1">LLM Cost</span>
                  <span className="text-cyan-300 font-bold">${(run?.total_llm_cost ?? summary?.total_llm_cost ?? 0).toFixed(6)}</span>
                </div>
                {summary?.models && summary.models.map((model) => (
                  <div key={model.model_key} className="p-2 bg-black/20 rounded">
                    <span className="text-white/40 block mb-1">{model.model_key}</span>
                    <span className="text-cyan-300">${model.total_cost.toFixed(6)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Quota Exhaustion Alert */}
        {quotaAlert && (
          <div className="max-w-7xl mx-auto w-full mb-6">
            <div className="glass-panel rounded-xl p-4 border border-amber-500/30 bg-amber-500/10 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
              <div>
                <h2 className="text-sm font-bold text-amber-400 mb-1">Quota Exhausted</h2>
                <p className="text-sm text-amber-200/80 leading-relaxed">{quotaAlert}</p>
              </div>
            </div>
          </div>
        )}

        {/* Main Content Grid */}
        <div className="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-3 gap-6 pb-12">
          <div className="lg:col-span-2 space-y-6">
            <LiveTranscript messages={messages} sseStatus={sseStatus} debugMode={run?.debug_mode ?? summary?.debug_mode ?? false} />
          </div>

          <div className="space-y-6">
            <Leaderboard models={summary?.models ?? []} />
            <EvidencePanel evidences={datasetInfo?.evidences ?? []} />
            <PressureScatter results={scores} />
            <ConfusionMatrix results={scores} />
            <CalibrationChart results={scores} />
            <FailGallery runId={runId} results={scores} />
          </div>
        </div>
      </div>
    </div>
  );
}
