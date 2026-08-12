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
    <div className="glass-panel rounded-2xl sm:rounded-3xl p-4 sm:p-8 relative overflow-hidden flex flex-col shadow-lg">
      {/* Scroll fade mask at top */}
      <div className="absolute top-0 left-0 right-0 h-12 bg-gradient-to-b from-[#FFFFFF] to-transparent z-10 pointer-events-none"></div>

      <div className="flex justify-between items-center mb-3 sm:mb-6">
        <h2 className="text-base sm:text-lg font-semibold text-[#412AD1]">Live Debate</h2>
        {debugMode && (
          <div className="flex gap-2">
            <div className={`text-[10px] font-mono px-2 py-1 rounded border ${sseStatus === "OPEN" ? "bg-[#29BC41]/20 text-[#29BC41] border-[#29BC41]/30" :
              sseStatus === "CONNECTING" ? "bg-[#FCC503]/20 text-[#292524] border-[#FCC503]/40" :
                "bg-[#B50BBB]/20 text-[#B50BBB] border-[#B50BBB]/30"
              }`}>
              SSE: {sseStatus || "UNKNOWN"}
            </div>
            <div className="hidden sm:block text-[10px] font-mono text-[#292524]/60 bg-[#292524]/5 px-2 py-1 rounded border border-[#292524]/10">
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
          <p className="text-sm text-[#292524]/60 text-center py-12">Waiting for agents...</p>
        )}
        {displayedMessages.map((msg, i) => {
          const alignRight = shouldAlignRight(msg.role);
          const avatarInitial = getAvatarInitial(msg.role);
          const avatarGradient = getAvatarGradient(msg.role);
          const roleColor = ROLE_COLORS[msg.role] ?? "text-[#412AD1]";

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
                className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br ${avatarGradient} flex items-center justify-center text-[10px] sm:text-xs font-bold shadow-md mt-1 flex-shrink-0`}
              >
                {avatarInitial}
              </div>

              {/* Message bubble */}
              <div
                className={`bg-[#FFFFFF] border p-3 sm:p-5 rounded-xl sm:rounded-2xl backdrop-blur-sm group-hover:border-[#412AD1]/30 transition-all ${alignRight ? "rounded-tr-none text-right" : "rounded-tl-none"
                  } ${isHighlighted
                    ? "border-[#412AD1]/60 bg-[#412AD1]/5 shadow-[0_0_20px_rgba(65,42,209,0.15)] ring-2 ring-[#412AD1]/20 scale-[1.01]"
                    : "border-[#292524]/12 shadow-sm"
                  } max-w-full sm:max-w-2xl`}
              >
                <div
                  className={`flex justify-between items-baseline mb-2 ${alignRight ? "flex-row-reverse" : ""
                    }`}
                >
                  <span className={`${roleColor} font-semibold text-sm`}>
                    {msg.role} Agent
                  </span>
                  <span className="text-[10px] text-[#292524]/50">
                    {i === messages.length - 1 ? "Just now" : `${messages.length - i - 1}s ago`}
                  </span>
                </div>

                {parsed ? (
                  <div className="text-[#292524]">{formatStructuredMessage(parsed, msg.role, msg.model_key)}</div>
                ) : (
                  <p className="text-sm sm:text-base font-normal leading-relaxed text-[#292524]">
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
