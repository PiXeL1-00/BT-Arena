/* Shared TypeScript interfaces. */

export type Verdict = "SUPPORTED" | "REFUTED" | "INSUFFICIENT";
export type RunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface Dataset {
  id: string;
  version: string;
  description: string;
  case_count: number;
}

export interface DatasetCase {
  case_id: string;
  topic: string;
  claim: string;
  pressure_score: number;
  label: Verdict;
  evidence_packets: Evidence[];
}

export interface Evidence {
  eid: string;
  summary: string;
  source: string;
  date: string;
}

export interface DatasetDetail {
  id: string;
  version: string;
  description: string;
  meta: Record<string, unknown>;
  cases: DatasetCase[];
}

export interface ModelConfig {
  id?: string;
  provider: string;
  model_name: string;
  api_key_env: string;
}

export interface RunRequest {
  dataset_id: string;
  case_id: string;
  models: ModelConfig[];
  mode: string;
}

export interface RunInfo {
  run_id: string;
  dataset_id: string;
  case_id: string;
  status: RunStatus;
  models: { provider: string; model_name: string }[];
  created_at: string;
  finished_at: string | null;
  total_llm_cost?: number;
  debug_mode?: boolean;
}

export interface CaseResult {
  case_id: string;
  model_key: string;
  verdict: Verdict;
  label: Verdict;
  score: number;
  passed: boolean;
  confidence: number;
  latency_ms: number;
  critical_fail_reason: string | null;
}

export interface ModelMetrics {
  model_key: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  critical_fails: number;
  pass_rate: number;
  avg_score: number;
  avg_latency_ms: number;
  total_cost: number;
  high_pressure_pass_rate: number;
  model_passes_eval: boolean;
}

export interface RunSummary {
  run_id: string;
  status: RunStatus;
  total_cases: number;
  models: ModelMetrics[];
  total_llm_cost?: number;
  debug_mode?: boolean;
}

export interface AgentMessage {
  role: string;
  model_key: string;
  content: string;
  phase?: string; // 'independent', 'cross_exam', 'revision', 'dispute', 'judge'
  round?: number; // Round number for context
  created_at?: string;
}


// SSEEvent is now defined in eventTypes.ts with proper discriminated union types

// Debate message schemas

// Phase 1: Proposals
export interface Proposal {
  proposed_verdict: string;
  evidence_used: string[];
  key_points: string[];
  uncertainties?: string[];
  what_would_change_my_mind?: string[];
}

// Phase 2: Cross-exam
export interface Question {
  to: string;
  q: string;
  evidence_refs: string[];
}

export interface QuestionsMessage {
  questions: Question[];
}

export interface Answer {
  q: string;
  a: string;
  evidence_refs: string[];
  admission: string;
}

export interface AnswersMessage {
  answers: Answer[];
}

// Phase 3: Revision
export interface Revision {
  final_proposed_verdict: string;
  evidence_used: string[];
  what_i_changed: string[];
  remaining_disagreements: string[];
  confidence: number;
}

// Phase 3.5: Dispute
export interface DisputeQuestion {
  q: string;
  evidence_refs: string[];
}

export interface DisputeQuestionsMessage {
  questions: DisputeQuestion[];
}

export interface DisputeAnswer {
  q: string;
  a: string;
  evidence_refs: string[];
  admission: string;
}

export interface DisputeAnswersMessage {
  answers: DisputeAnswer[];
}

// Phase 4: Judge
export interface JudgeDecision {
  verdict: string;
  confidence: number;
  evidence_used: string[];
  reasoning: string;
}

// Union type for all possible structured messages
export type StructuredMessage =
  | Proposal
  | QuestionsMessage
  | AnswersMessage
  | Revision
  | DisputeQuestionsMessage
  | DisputeAnswersMessage
  | JudgeDecision;

export type MessageType =
  | "proposal"
  | "questions"
  | "answers"
  | "revision"
  | "dispute_questions"
  | "dispute_answers"
  | "judge_decision"
  | "unknown";

export interface ParsedMessage {
  type: MessageType;
  data: StructuredMessage;
  isTruncated: boolean;
}

// API Key Validation Types
export type KeyValidationStatus =
  | "VALID"
  | "INVALID_KEY"
  | "NO_FUNDS_OR_BUDGET"
  | "RATE_LIMIT"
  | "PERMISSION_OR_REGION"
  | "PROVIDER_OUTAGE"
  | "TIMEOUT"
  | "UNKNOWN_ERROR";

export interface KeyValidationResult {
  status: KeyValidationStatus;
  provider: string;
  api_key_env: string;
  error_message: string | null;
  request_id: string | null;
  http_status: number | null;
  validated_at: string | null;
}

export interface AvailableKeysResponse {
  available_keys: string[];
  validation?: Record<string, KeyValidationResult>;
  validation_error?: string;
}