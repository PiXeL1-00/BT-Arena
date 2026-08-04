/* Available models (6 providers) and API config. */

export const API_BASE = "/api";

// SSE must bypass the Next.js rewrite proxy (which buffers the response body).
// EventSource connects directly to the backend for real-time streaming.
export const SSE_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "";

export interface AvailableModel {
  id: string;
  provider: string;
  model_name: string;
  label: string;
  api_key_env: string;
}

/** @deprecated — models are now fetched from GET /models/registry. This is only a compile-time fallback. */
export const AVAILABLE_MODELS: AvailableModel[] = [];

export const ROLE_COLORS: Record<string, string> = {
  Orthodox: "text-cyan-300",
  Heretic: "text-pink-300",
  Skeptic: "text-amber-300",
  Judge: "text-emerald-300",
};