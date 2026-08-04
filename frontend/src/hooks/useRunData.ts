"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { RunInfo, RunSummary, RunStatus } from "@/lib/types";

const TERMINAL_STATUSES: RunStatus[] = ["COMPLETED", "FAILED"];

export function useRunData(runId: string | null) {
  const [run, setRun] = useState<RunInfo | null>(null);
  const [summary, setSummary] = useState<RunSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!runId) return;
    try {
      const [r, s] = await Promise.all([
        api.getRun(runId),
        api.getRunSummary(runId),
      ]);
      setRun(r);
      setSummary(s);
      if (TERMINAL_STATUSES.includes(r.status)) {
        stopPolling();
      }
    } catch {
      // run may not exist yet
    } finally {
      setLoading(false);
    }
  }, [runId, stopPolling]);

  useEffect(() => {
    refresh();
    timerRef.current = setInterval(refresh, 3000);
    return stopPolling;
  }, [refresh, stopPolling]);

  return { run, summary, loading, refresh };
}
