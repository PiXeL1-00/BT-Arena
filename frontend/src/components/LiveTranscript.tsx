"use client";

import { useRef, useEffect, useState } from "react";
import type { AgentMessage } from "@/lib/types";
import { parseStructuredMessage } from "@/lib/messageParser";
import { formatStructuredMessage } from "@/lib/messageFormatter";
import { ROLE_COLORS } from "@/lib/constants";

interface Props {
  messages: AgentMessage[];
  sseStatus?: string;
  debugMode?: boolean;
}

function getAvatarInitial(role: string): string {
  const roleMap: Record<string, string> = {
    Orthodox: "O",
    Heretic: "H",
    Skeptic: "S",
    Judge: "J",
  };
  return roleMap[role] || role[0]?.toUpperCase() || "?";
}

function getAvatarGradient(role: string): string {
  const gradientMap: Record<string, string> = {
    Orthodox: "from-blue-400 to-cyan-500",
    Heretic: "from-rose-500 to-orange-600",
    Skeptic: "from-amber-400 to-yellow-600",
    Judge: "from-emerald-400 to-teal-500",
  };
  return gradientMap[role] || "from-gray-400 to-gray-500";
}

function shouldAlignRight(role: string): boolean {
  return role === "Heretic";
}

export function LiveTranscript({ messages, sseStatus, debugMode }: Props) {
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

  // Effect to highlight and scroll when a new message is displayed
  useEffect(() => {
    if (displayedMessages.length > 0) {
      const newIndex = displayedMessages.length - 1;
      setHighlightedIndex(newIndex);

      // Scroll to the new message element immediately
      requestAnimationFrame(() => {
        const newMessageElement = messageRefs.current.get(newIndex);
        if (newMessageElement) {
          newMessageElement.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
            inline: "nearest",
          });
        }
      });

      // Remove highlight after 2 seconds
      const clearHighlightTimer = setTimeout(() => {
        setHighlightedIndex(null);
      }, 2000);

      return () => clearTimeout(clearHighlightTimer);
    }
  }, [displayedMessages.length]);

  return (
    <div className="glass-panel rounded-2xl sm:rounded-3xl p-4 sm:p-8 relative overflow-hidden flex flex-col">
      {/* Scroll fade mask at top */}
      <div className="absolute top-0 left-0 right-0 h-12 bg-gradient-to-b from-[rgba(255,255,255,0.05)] to-transparent z-10 pointer-events-none"></div>

      <div className="flex justify-between items-center mb-3 sm:mb-6">
        <h2 className="text-base sm:text-lg font-medium text-cyan-300">Live Debate</h2>
        {debugMode && (
          <div className="flex gap-2">
            <div className={`text-[10px] font-mono px-2 py-1 rounded border ${sseStatus === "OPEN" ? "bg-green-500/20 text-green-300 border-green-500/30" :
              sseStatus === "CONNECTING" ? "bg-yellow-500/20 text-yellow-300 border-yellow-500/30" :
                "bg-red-500/20 text-red-300 border-red-500/30"
              }`}>
              SSE: {sseStatus || "UNKNOWN"}
            </div>
            <div className="hidden sm:block text-[10px] font-mono text-white/30 bg-black/20 px-2 py-1 rounded border border-white/5">
              DEBUG: S={messages.length} D={displayedMessages.length} Q={queueRef.current.length}
            </div>
          </div>
        )}
      </div>

      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto space-y-4 sm:space-y-8 pr-1 sm:pr-2 relative z-0 hide-scrollbar"
      >
        {messages.length === 0 && (
          <p className="text-sm text-white/50 text-center py-12">Waiting for agents...</p>
        )}
        {displayedMessages.map((msg, i) => {
          const alignRight = shouldAlignRight(msg.role);
          const avatarInitial = getAvatarInitial(msg.role);
          const avatarGradient = getAvatarGradient(msg.role);
          const roleColor = ROLE_COLORS[msg.role] ?? "text-white/60";

          // Try to parse structured message (JSON or TOML)
          const parsed = parseStructuredMessage(msg.content, msg.phase);
          const isHighlighted = highlightedIndex === i;

          return (
            <div
              key={i}
              ref={(el) => {
                if (el) {
                  messageRefs.current.set(i, el);
                } else {
                  messageRefs.current.delete(i);
                }
              }}
              className={`flex gap-2 sm:gap-4 items-start group ${alignRight ? "flex-row-reverse" : ""} transition-all duration-500 ${isHighlighted
                ? "animate-in fade-in slide-in-from-bottom-2 duration-500"
                : ""
                }`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br ${avatarGradient} flex items-center justify-center text-[10px] sm:text-xs font-bold shadow-glow mt-1 flex-shrink-0`}
              >
                {avatarInitial}
              </div>

              {/* Message bubble */}
              <div
                className={`bg-white/10 border p-3 sm:p-5 rounded-xl sm:rounded-2xl backdrop-blur-sm group-hover:bg-white/15 transition-all ${alignRight ? "rounded-tr-none text-right" : "rounded-tl-none"
                  } ${isHighlighted
                    ? "border-cyan-400/60 bg-cyan-500/10 shadow-[0_0_30px_rgba(34,211,238,0.4)] ring-2 ring-cyan-400/30 scale-[1.02]"
                    : "border-white/5"
                  } max-w-full sm:max-w-2xl`}
              >
                <div
                  className={`flex justify-between items-baseline mb-2 ${alignRight ? "flex-row-reverse" : ""
                    }`}
                >
                  <span className={`${roleColor} font-medium text-sm`}>
                    {msg.role} Agent
                  </span>
                  <span className="text-[10px] text-white/30">
                    {i === messages.length - 1 ? "Just now" : `${messages.length - i - 1}s ago`}
                  </span>
                </div>

                {parsed ? (
                  <div className="text-white/90">{formatStructuredMessage(parsed, msg.role, msg.model_key)}</div>
                ) : (
                  <p className="text-sm sm:text-lg font-light leading-relaxed text-white/90">
                    {msg.content}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
