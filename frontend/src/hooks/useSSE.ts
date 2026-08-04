"use client";

import { useEffect, useRef, useState } from "react";
import type { SSEEvent } from "@/lib/eventTypes";

/**
 * Hook that connects to an SSE endpoint and dispatches parsed events.
 */
export type SSEStatus = "CONNECTING" | "OPEN" | "CLOSED" | "ERROR";

export function useSSE(
  url: string | null,
  onEvent: (event: SSEEvent) => void,
): SSEStatus {
  const [status, setStatus] = useState<SSEStatus>("CLOSED");
  const cbRef = useRef(onEvent);
  cbRef.current = onEvent;

  useEffect(() => {
    if (!url) {
      setStatus("CLOSED");
      return;
    }

    console.log(`[useSSE] Connecting to ${url}...`);
    setStatus("CONNECTING");

    const es = new EventSource(url);

    es.onopen = () => {
      console.log(`[useSSE] Connected to ${url}`);
      setStatus("OPEN");
    };

    es.onmessage = (e) => {
      try {
        const data: SSEEvent = JSON.parse(e.data);
        cbRef.current(data);
      } catch (err) {
        console.error("[useSSE] Failed to parse event:", e.data, err);
      }
    };

    es.onerror = (e) => {
      console.error("[useSSE] Connection error:", e);
      setStatus("ERROR");
      // EventSource will retry automatically, but we mark as error
    };

    return () => {
      console.log(`[useSSE] Closing connection to ${url}`);
      es.close();
      setStatus("CLOSED");
    };
  }, [url]);

  return status;
}
