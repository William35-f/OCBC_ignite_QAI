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
