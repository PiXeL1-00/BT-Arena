"use client";

import { useRef, useEffect, useState } from "react";
import { Zap, RefreshCw, Gavel } from "lucide-react";
import type { AgentMessage } from "@/lib/types";
import type { ModelRegistryEntry } from "@/lib/api";
import { parseStructuredMessage } from "@/lib/messageParser";
import { formatStructuredMessage } from "@/lib/messageFormatter";
import { ROLE_COLORS } from "@/lib/constants";

interface Props {
  messages: AgentMessage[];
  sseStatus?: string;
  debugMode?: boolean;
  models?: ModelRegistryEntry[];
  onModelChange?: (messageIndex: number, newModelKey: string) => void;
  isModelDisabled?: (model: ModelRegistryEntry) => boolean;
  getModelUsageRemaining?: (model: ModelRegistryEntry) => number | null;
  regeneratingIndex?: number | null;
  /** Raw debateConfig for usage_today access in debug mode */
  debateConfig?: { usage_today: Record<string, number>; daily_cap: number; debug_mode: boolean } | null;
}

function getAvatarInitial(role: string): string {
  const roleMap: Record<string, string> = {
    Orthodox: "O",
    Heretic: "H",
    Skeptic: "S",
    Judge: "⚖",
  };
  return roleMap[role] || role[0]?.toUpperCase() || "?";
}

function getAvatarGradient(role: string): string {
  const gradientMap: Record<string, string> = {
    Orthodox: "from-[#412AD1] to-[#412AD1]/80 text-[#FFFFFF]",
    Heretic: "from-[#B50BBB] to-[#B50BBB]/80 text-[#FFFFFF]",
    Skeptic: "from-[#FCC503] to-[#FCC503]/80 text-[#0C0A09]",
    Judge: "from-[#29BC41] to-[#29BC41]/80 text-[#FFFFFF]",
  };
  return gradientMap[role] || "from-[#292524]/20 to-[#292524]/40 text-[#292524]";
}

function shouldAlignRight(role: string): boolean {
  return role === "Heretic";
}

function AgentModelControl({
  currentModelKey,
  models,
  onModelChange,
  isModelDisabled,
  getModelUsageRemaining,
  debateConfig,
  isDisabled,
}: {
  currentModelKey: string;
  models?: ModelRegistryEntry[];
  onModelChange?: (newModelKey: string) => void;
  isModelDisabled?: (model: ModelRegistryEntry) => boolean;
  getModelUsageRemaining?: (model: ModelRegistryEntry) => number | null;
  debateConfig?: Props["debateConfig"];
  isDisabled?: boolean;
}) {
  const selectedModel = models?.find(
    (m) => `${m.provider}/${m.model_name}` === currentModelKey || m.id === currentModelKey
  );

  // Try standard hook first; fall back to raw usage_today for debug mode
  let remaining: number | null = selectedModel && getModelUsageRemaining
    ? getModelUsageRemaining(selectedModel)
    : null;

  if (remaining === null && selectedModel && debateConfig) {
    const modelKey = `${selectedModel.provider}/${selectedModel.model_name}`;
    const used = debateConfig.usage_today[modelKey] ?? 0;
    remaining = Math.max(0, debateConfig.daily_cap - used);
  }

  if (!models || models.length === 0) {
    return (
      <div className="flex items-center gap-1.5 font-mono text-[10px] text-[#292524]/50 bg-[#292524]/5 px-2 py-0.5 rounded-full">
        <span className="truncate max-w-[120px]">{currentModelKey.split("/").pop()}</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {/* Model Selector Dropdown — single, compact */}
      <select
        value={currentModelKey}
        onChange={(e) => onModelChange?.(e.target.value)}
        disabled={isDisabled}
        title="Switch model — debate regenerates from this turn onwards"
        className="bg-[#F8F7FF] border border-[#412AD1]/20 hover:border-[#412AD1]/50 rounded-lg px-2 py-0.5 text-[10px] font-mono text-[#412AD1] focus:outline-none focus:ring-1 focus:ring-[#412AD1]/30 transition-all cursor-pointer disabled:opacity-40 max-w-[160px] truncate"
      >
        {models.map((m) => {
          const modelKey = `${m.provider}/${m.model_name}`;
          const disabled = isModelDisabled?.(m) ?? false;
          return (
            <option key={m.id} value={modelKey} disabled={disabled}>
              {m.label}
            </option>
          );
        })}
      </select>

      {/* Credit / Usage Badge */}
      <span
        className={`inline-flex items-center gap-0.5 text-[10px] font-mono px-1.5 py-0.5 rounded-full border ${
          remaining !== null && remaining <= 5
            ? "bg-[#B50BBB]/10 border-[#B50BBB]/25 text-[#B50BBB]"
            : "bg-[#29BC41]/10 border-[#29BC41]/25 text-[#29BC41]"
        }`}
        title={remaining !== null ? `${remaining} calls remaining today for this model` : "Unlimited / debug mode"}
      >
        <Zap className="w-2.5 h-2.5" />
        {remaining !== null ? `${remaining}` : "∞"}
      </span>
    </div>
  );
}

export function LiveTranscript({
  messages,
  sseStatus,
  debugMode,
  models,
  onModelChange,
  isModelDisabled,
  getModelUsageRemaining,
  regeneratingIndex,
  debateConfig,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [displayedMessages, setDisplayedMessages] = useState<AgentMessage[]>([]);
  const [highlightedIndex, setHighlightedIndex] = useState<number | null>(null);
  const messageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const processedCountRef = useRef(0);
  const queueRef = useRef<AgentMessage[]>([]);
  const isProcessingRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const processQueue = () => {
    if (queueRef.current.length === 0) {
      isProcessingRef.current = false;
      return;
    }
    isProcessingRef.current = true;
    const nextMsg = queueRef.current.shift();
    if (nextMsg) {
      setDisplayedMessages((prev) => [...prev, nextMsg]);
      timerRef.current = setTimeout(processQueue, 600);
    } else {
      isProcessingRef.current = false;
    }
  };

  useEffect(() => {
    if (messages.length === 0) {
      setDisplayedMessages([]);
      queueRef.current = [];
      processedCountRef.current = 0;
      return;
    }

    if (messages.length < displayedMessages.length) {
      // Messages were truncated for regeneration
      setDisplayedMessages(messages.slice());
      queueRef.current = [];
      processedCountRef.current = messages.length;
      return;
    }

    if (messages.length > processedCountRef.current) {
      const newMessages = messages.slice(processedCountRef.current);
      queueRef.current.push(...newMessages);
      processedCountRef.current = messages.length;
      if (!isProcessingRef.current) {
        processQueue();
      }
    }
  }, [messages]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      queueRef.current = [];
      isProcessingRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (displayedMessages.length > 0) {
      const newIndex = displayedMessages.length - 1;
      setHighlightedIndex(newIndex);
      requestAnimationFrame(() => {
        const el = messageRefs.current.get(newIndex);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
      const t = setTimeout(() => setHighlightedIndex(null), 2000);
      return () => clearTimeout(t);
    }
  }, [displayedMessages.length]);

  return (
    <div className="glass-panel rounded-2xl sm:rounded-3xl p-4 sm:p-8 relative overflow-hidden flex flex-col shadow-lg">
      {/* Scroll fade mask at top */}
      <div className="absolute top-0 left-0 right-0 h-12 bg-gradient-to-b from-[#FFFFFF] to-transparent z-10 pointer-events-none" />

      <div className="flex justify-between items-center mb-3 sm:mb-6">
        <h2 className="text-base sm:text-lg font-semibold text-[#412AD1]">Live Debate</h2>
        {debugMode && (
          <div className="flex gap-2">
            <div className={`text-[10px] font-mono px-2 py-1 rounded border ${sseStatus === "OPEN"
              ? "bg-[#29BC41]/20 text-[#29BC41] border-[#29BC41]/30"
              : sseStatus === "CONNECTING"
              ? "bg-[#FCC503]/20 text-[#292524] border-[#FCC503]/40"
              : "bg-[#B50BBB]/20 text-[#B50BBB] border-[#B50BBB]/30"
            }`}>
              SSE: {sseStatus || "UNKNOWN"}
            </div>
            <div className="hidden sm:block text-[10px] font-mono text-[#292524]/60 bg-[#292524]/5 px-2 py-1 rounded border border-[#292524]/10">
              S={messages.length} D={displayedMessages.length} Q={queueRef.current.length}
            </div>
          </div>
        )}
      </div>

      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto space-y-4 sm:space-y-6 pr-1 sm:pr-2 relative z-0 hide-scrollbar"
      >
        {messages.length === 0 && (
          <p className="text-sm text-[#292524]/60 text-center py-12">Waiting for agents...</p>
        )}

        {displayedMessages.map((msg, i) => {
          const isJudge = msg.role === "Judge";
          const alignRight = shouldAlignRight(msg.role);
          const avatarInitial = getAvatarInitial(msg.role);
          const avatarGradient = getAvatarGradient(msg.role);
          const roleColor = ROLE_COLORS[msg.role] ?? "text-[#412AD1]";
          const parsed = parseStructuredMessage(msg.content, msg.phase);
          const isHighlighted = highlightedIndex === i;
          const isRegeneratingThis = regeneratingIndex === i;
          const isRegenerating = regeneratingIndex !== null && regeneratingIndex !== undefined;

          const modelControl = (
            <AgentModelControl
              currentModelKey={msg.model_key}
              models={models}
              onModelChange={(newModelKey) => onModelChange?.(i, newModelKey)}
              isModelDisabled={isModelDisabled}
              getModelUsageRemaining={getModelUsageRemaining}
              debateConfig={debateConfig}
              isDisabled={isRegenerating}
            />
          );

          if (isJudge) {
            // ── Judge bubble — full-width, visually distinct verdict card ──
            return (
              <div
                key={i}
                ref={(el) => {
                  if (el) messageRefs.current.set(i, el);
                  else messageRefs.current.delete(i);
                }}
                className={`w-full transition-all duration-700 ${isHighlighted ? "animate-in fade-in slide-in-from-bottom-2 duration-700" : ""}`}
              >
                {/* Divider with label */}
                <div className="flex items-center gap-3 mb-4 mt-2">
                  <div className="flex-1 h-px bg-gradient-to-r from-transparent via-[#29BC41]/40 to-transparent" />
                  <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#29BC41]/10 border border-[#29BC41]/30">
                    <Gavel className="w-3.5 h-3.5 text-[#29BC41]" />
                    <span className="text-xs font-bold tracking-widest text-[#29BC41] uppercase">Final Verdict</span>
                  </div>
                  <div className="flex-1 h-px bg-gradient-to-l from-transparent via-[#29BC41]/40 to-transparent" />
                </div>

                {/* Judge card */}
                <div
                  className={`w-full rounded-2xl border-2 overflow-hidden shadow-lg transition-all ${
                    isHighlighted
                      ? "border-[#29BC41]/70 shadow-[0_0_30px_rgba(41,188,65,0.2)]"
                      : "border-[#29BC41]/25 shadow-[0_4px_20px_rgba(41,188,65,0.08)]"
                  }`}
                  style={{ background: "linear-gradient(135deg, rgba(41,188,65,0.04) 0%, rgba(255,255,255,0.98) 50%, rgba(41,188,65,0.02) 100%)" }}
                >
                  {/* Judge header bar */}
                  <div className="flex items-center justify-between px-4 py-3 border-b border-[#29BC41]/15 bg-[#29BC41]/5">
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-full bg-gradient-to-br ${avatarGradient} flex items-center justify-center text-sm font-bold shadow-md`}>
                        {avatarInitial}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-[#29BC41]">Judge</span>
                          <span className="text-[10px] bg-[#29BC41]/15 text-[#29BC41] font-bold tracking-wider px-2 py-0.5 rounded-full border border-[#29BC41]/25 uppercase">
                            Conclusion
                          </span>
                        </div>
                        <span className="text-[10px] text-[#292524]/40">Final ruling on the debate</span>
                      </div>
                    </div>
                    {modelControl}
                  </div>

                  {/* Judge content */}
                  <div className="p-4 sm:p-6">
                    {isRegeneratingThis && (
                      <div className="mb-4 p-3 rounded-xl bg-[#412AD1]/10 border border-[#412AD1]/20 text-[#412AD1] text-xs flex items-center gap-2 animate-pulse">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        Regenerating debate from turn {i + 1} onwards with new model...
                      </div>
                    )}
                    {parsed ? (
                      <div className="text-[#292524]">{formatStructuredMessage(parsed, msg.role, msg.model_key)}</div>
                    ) : (
                      <p className="text-sm sm:text-base font-normal leading-relaxed text-[#292524]">{msg.content}</p>
                    )}
                  </div>
                </div>
              </div>
            );
          }

          // ── Regular agent bubble ──
          return (
            <div
              key={i}
              ref={(el) => {
                if (el) messageRefs.current.set(i, el);
                else messageRefs.current.delete(i);
              }}
              className={`flex gap-2 sm:gap-4 items-start group ${alignRight ? "flex-row-reverse" : ""} transition-all duration-500 ${
                isHighlighted ? "animate-in fade-in slide-in-from-bottom-2 duration-500" : ""
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br ${avatarGradient} flex items-center justify-center text-[10px] sm:text-xs font-bold shadow-md mt-1 flex-shrink-0`}
              >
                {avatarInitial}
              </div>

              {/* Message bubble */}
              <div
                className={`bg-[#FFFFFF] border p-3 sm:p-5 rounded-xl sm:rounded-2xl backdrop-blur-sm group-hover:border-[#412AD1]/25 transition-all ${
                  alignRight ? "rounded-tr-none" : "rounded-tl-none"
                } ${
                  isHighlighted
                    ? "border-[#412AD1]/50 bg-[#412AD1]/5 shadow-[0_0_20px_rgba(65,42,209,0.12)] ring-2 ring-[#412AD1]/15 scale-[1.01]"
                    : "border-[#292524]/10 shadow-sm"
                } max-w-full sm:max-w-2xl flex-1 min-w-0`}
              >
                {/* Bubble header */}
                <div className={`flex items-center justify-between gap-2 mb-3 pb-2 border-b border-[#292524]/5 flex-wrap ${alignRight ? "flex-row-reverse" : ""}`}>
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`${roleColor} font-semibold text-sm truncate`}>
                      {msg.role} Agent
                    </span>
                    <span className="text-[10px] text-[#292524]/40 flex-shrink-0">
                      {i === messages.length - 1 ? "Just now" : `turn ${i + 1}`}
                    </span>
                  </div>
                  {modelControl}
                </div>

                {isRegeneratingThis && (
                  <div className="mb-3 p-2.5 rounded-lg bg-[#412AD1]/10 border border-[#412AD1]/20 text-[#412AD1] text-xs flex items-center gap-2 animate-pulse">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Regenerating from turn {i + 1} onwards with new model...
                  </div>
                )}

                {parsed ? (
                  <div className="text-[#292524]">{formatStructuredMessage(parsed, msg.role, msg.model_key)}</div>
                ) : (
                  <p className="text-sm sm:text-base font-normal leading-relaxed text-[#292524]">{msg.content}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
