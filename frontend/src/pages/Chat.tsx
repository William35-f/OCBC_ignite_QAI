// Employee chat: ask OCBC AI a question; Q AI checks the prompt and the answer.
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, type Run, type Scenario } from "../api";
import RunCard from "../components/RunCard";
import { EmptyState, ErrorNote } from "../components/ui";

const THREAD_KEY = "qai-thread";

function loadThread(): Run[] {
  try {
    return JSON.parse(sessionStorage.getItem(THREAD_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export default function Chat() {
  const [thread, setThread] = useState<Run[]>(loadThread);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [question, setQuestion] = useState("");
  const [hint, setHint] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get<Scenario[]>("/api/chat/scenarios").then(setScenarios).catch(() => {});
  }, []);

  useEffect(() => {
    try {
      sessionStorage.setItem(THREAD_KEY, JSON.stringify(thread));
    } catch {
      /* storage blocked */
    }
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [thread.length]);

  const ask = async (e: FormEvent) => {
    e.preventDefault();
    if (question.trim().length < 3) return;
    setBusy(true);
    setError("");
    try {
      const run = await api.post<Run>("/api/chat/ask", { question });
      setThread((t) => [...t, run]);
      setQuestion("");
      setHint("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const pickScenario = (id: string) => {
    const s = scenarios.find((x) => x.id === id);
    if (!s) return;
    setQuestion(s.question);
    setHint(s.hint);
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Ask OCBC AI</h1>
          <p className="muted">Every question and answer is checked by Q AI before you act on it.</p>
        </div>
        <div className="flex w-full items-center gap-2 sm:w-auto">
          {thread.length > 0 && (
            <button className="shrink-0 text-sm font-medium text-ink-muted hover:text-ink" onClick={() => setThread([])}>
              Clear chat
            </button>
          )}
          <select
            aria-label="Demo scenarios"
            className="input min-w-0 flex-1 sm:w-auto sm:flex-none"
            value=""
            onChange={(e) => pickScenario(e.target.value)}
          >
            <option value="" disabled>
              Demo scenarios…
            </option>
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <section className="space-y-6">
        {thread.length === 0 && (
          <EmptyState title="No questions yet">
            Type a question about a procedure, or pick one from “Demo scenarios”.
          </EmptyState>
        )}
        {thread.map((r) => (
          <RunCard key={r.id} initial={r} />
        ))}
        <div ref={bottom} />
      </section>

      <form onSubmit={ask} className="card sticky bottom-3 space-y-2 p-3 shadow-md">
        {hint && <p className="px-1 text-xs text-ink-muted">Demo tip: {hint}</p>}
        <div className="flex gap-2">
          <label htmlFor="question" className="sr-only">
            Your question
          </label>
          <input
            id="question"
            className="input"
            placeholder="e.g. What's the daily overseas transfer limit?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={1000}
          />
          <button className="btn-primary shrink-0" disabled={busy || question.trim().length < 3}>
            {busy ? "Checking…" : "Ask"}
          </button>
        </div>
        {error && <ErrorNote message={error} />}
      </form>
    </div>
  );
}
