// Small typed wrapper around the backend API (proxied to FastAPI by Vite).

const BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the Q AI backend. Is it running on port 8000?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* not JSON */
    }
    throw new ApiError(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T,>(path: string) => request<T>("GET", path),
  post: <T,>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T,>(path: string, body: unknown) => request<T>("PUT", path, body),
};

// ---- Shared types -------------------------------------------------------

export interface RequiredDetail {
  name: string;
  question: string;
  options: string[];
}

export interface KBDocument {
  id: string;
  label: string;
  title: string;
  version: string;
  topic: string;
  status: "current" | "superseded";
  effective_date: string;
  superseded_by: string | null;
  owner: string;
  required_details: RequiredDetail[];
  retriever_enabled: boolean;
  passages: { section: string; section_label: string; heading: string; text: string; kind: string }[];
  conditions: { id: string; when: string; text: string; key_phrase: string }[];
}

export interface ConflictRow {
  id: number;
  topic: string;
  field: string;
  doc_a: string;
  doc_a_label: string;
  value_a: string;
  doc_b: string;
  doc_b_label: string;
  value_b: string;
}

export interface AppSettings {
  llm_provider: "mock" | "openai";
  similarity_threshold: number;
  max_followups: number;
  openai_configured: boolean;
}

// ---- Workflow -----------------------------------------------------------

export interface FollowUp {
  name: string;
  question: string;
  options: string[];
}

export interface Evidence {
  doc_id: string;
  doc_label: string;
  version: string;
  status: string;
  section: string;
  section_label: string;
  effective_date: string;
  text: string;
  score: number;
}

export interface ClaimResult {
  index: number;
  text: string;
  label: string;
  reason: string;
  correction: string | null;
  evidence: Evidence[];
  ignored_conflicting: string[];
}

export interface PromptCheck {
  parts: string[];
  topic: string;
  missing_details: FollowUp[];
  assumptions: string[];
  search_query: string;
  known_details: Record<string, string>;
  details_used: Record<string, string>;
  assumption_checks: ClaimResult[];
  correction_notes: string[];
  matched_document: string | null;
}

export type RunStatus = "checking_prompt" | "needs_details" | "running" | "done" | "error";

export interface Run {
  review: ReviewItem | null;
  report_reason: string | null;
  employee_action_at: string | null;
  source: string;
  user_name: string;
  id: number;
  created_at: string;
  question: string;
  details: Record<string, string>;
  status: RunStatus;
  stage: string;
  error: string | null;
  prompt_check: PromptCheck | null;
  topic: string | null;
  original_answer: string | null;
  original_checks: Checks | null;
  original_verdict: Verdict | null;
  retried: boolean;
  retry_feedback: string | null;
  what_changed: { type: "same" | "removed" | "added"; text: string }[];
  retry_answer: string | null;
  retry_checks: Checks | null;
  retry_verdict: Verdict | null;
  final_answer: string | null;
  final_verdict: Verdict | null;
  routed_to: string | null;
  employee_action: string | null;
}

export interface Scenario {
  id: string;
  label: string;
  question: string;
  hint: string;
}

export type Verdict = "Green" | "Amber" | "Red";

export interface Flag {
  check: "A" | "B" | "C";
  type: string;
  severity: "critical" | "warning" | "info";
  message: string;
  sentence_index: number | null;
  doc_ids: string[];
}

export interface SentenceView {
  index: number;
  text: string;
  raw: string;
  citations: { label: string; sections: string[]; doc_id: string | null; status: string; own: boolean }[];
  label: string;
  reason: string;
  correction: string | null;
  evidence: Evidence[];
  ignored_conflicting: string[];
  flag_types: string[];
}

export interface Checks {
  verdict: Verdict;
  flags: Flag[];
  sentences: SentenceView[];
  rule: Record<"citation_exists" | "source_current" | "figures_match" | "quotes_match", { passed: boolean; detail: unknown[] }>;
  source: { exceptions: unknown[]; cited_doc_ids: string[]; skipped_sentences: number[] };
  intent: { part: string; status: "answered" | "partly" | "not_answered"; reason: string }[];
  ignored_figures: string[];
}

// ---- Review ---------------------------------------------------------------

export interface ReviewItem {
  id: number;
  run_id: number;
  created_at: string;
  queue_reason: "red" | "amber_after_retry" | "reported" | "used_after_amber";
  main_flag: string;
  status: "pending" | "approved" | "corrected" | "rejected";
  reviewer: string | null;
  corrected_answer: string | null;
  decision_reason: string | null;
  decided_at: string | null;
}

export interface QueueRow extends ReviewItem {
  question: string;
  verdict: Verdict | null;
  first_verdict: Verdict | null;
  retried: boolean;
  user_name: string;
}

export interface GoldenRow {
  id: number;
  created_at: string;
  question: string;
  details: Record<string, string>;
  correct_answer: string;
  source_docs: string[];
  review_id: number | null;
}

// ---- Admin -------------------------------------------------------------------

export interface Dashboard {
  totals: {
    answers: number;
    green: number;
    amber: number;
    red: number;
    retried: number;
    fixed_by_retry: number;
    pending_reviews: number;
    used: number;
    reported: number;
    golden: number;
  };
  verdicts_over_time: { day: string; Green: number; Amber: number; Red: number }[];
  flag_counts: { type: string; count: number }[];
  topic_failures: { topic: string; failed: number; total: number }[];
  doc_errors: { doc_id: string; doc_label: string; errors: Record<string, number>; total: number }[];
  reviewer_decisions: { approved: number; corrected: number; rejected: number };
}

export interface Suggestion {
  id: string;
  kind: "retire_document" | "resolve_conflict" | "add_coverage";
  target: string;
  title: string;
  evidence: string;
  count: number;
  status: "open" | "applied" | "done";
  can_apply: boolean;
}

export interface RetestResult {
  id: number;
  created_at: string;
  passed: boolean;
  passed_count: number;
  total: number;
  results: {
    kind: "golden" | "held-out";
    question: string;
    details: Record<string, string>;
    expected: string;
    got: string | null;
    passed: boolean;
    reason: string;
    answer: string | null;
  }[];
}

export interface ActivityRow {
  id: number;
  at: string;
  event: string;
  actor: string;
  run_id: number | null;
  question: string | null;
  data: Record<string, unknown>;
}

// ---- Eval and Trust Challenge ----------------------------------------------

export interface EvalResults {
  run_at: string;
  provider: string;
  cases: number;
  verdict_accuracy: number;
  missed_errors: { count: number; of: number; ids: string[] };
  false_flags: { count: number; of: number; ids: string[] };
  per_check_accuracy: { A: number; B: number; C: number };
  flag_recall: number | null;
  by_type: Record<string, { cases: number; verdict_ok: number }>;
  retry: { amber_first: number; fixed: number; rate: number | null };
  rows: {
    id: string;
    type: string;
    question: string;
    expected_verdict: string;
    got_verdict: string;
    verdict_ok: boolean;
    expected_flags: string[];
    got_flags: string[];
    missing_flags: string[];
    per_check: { A: boolean; B: boolean; C: boolean };
  }[];
}

export interface TrustItem {
  id: string;
  question: string;
  answer: string;
  checks: Checks;
}

export interface RoundScore {
  answers: number;
  correct: number;
  accuracy: number | null;
}

export interface TrustSummary {
  participants: number;
  completed: number;
  A: RoundScore;
  B: RoundScore;
}
