// Settings: LLM provider, similarity threshold, max follow-up questions.
import { useEffect, useState } from "react";
import { api, type AppSettings } from "../api";
import { Badge, ErrorNote, Spinner } from "../components/ui";

export default function Settings() {
  const [s, setS] = useState<AppSettings | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [test, setTest] = useState<{ ok: boolean; error?: string } | null>(null);

  useEffect(() => {
    api.get<AppSettings>("/api/settings").then(setS).catch((e) => setError(e.message));
  }, []);

  const save = async () => {
    if (!s) return;
    setError("");
    setTest(null);
    try {
      setS(await api.put<AppSettings>("/api/settings", s));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const runTest = async () => {
    setTest(null);
    setTest(await api.post<{ ok: boolean; error?: string }>("/api/settings/test"));
  };

  if (!s) return error ? <ErrorNote message={error} /> : <Spinner />;

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="page-title">Settings</h1>
      {error && <ErrorNote message={error} />}

      <section className="card space-y-3">
        <h2 className="font-bold">LLM provider</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {(["mock", "openai"] as const).map((p) => (
            <label
              key={p}
              className={`cursor-pointer rounded-xl border p-3 ${s.llm_provider === p ? "border-brand bg-brand-tint" : "border-line"}`}
            >
              <input
                type="radio"
                name="provider"
                className="mr-2 accent-brand"
                checked={s.llm_provider === p}
                onChange={() => setS({ ...s, llm_provider: p })}
              />
              <span className="font-semibold">{p === "mock" ? "Mock (offline)" : "OpenAI / Azure OpenAI"}</span>
              <p className="mt-1 text-xs text-ink-muted">
                {p === "mock"
                  ? "Deterministic, no API key. Scripted demo scenarios plus simple rules."
                  : "Uses the keys in backend/.env."}
              </p>
            </label>
          ))}
        </div>
        {s.llm_provider === "openai" && !s.openai_configured && (
          <p className="text-sm text-warn">
            No OpenAI or Azure OpenAI key found in backend/.env. Add one and restart the backend.
          </p>
        )}
      </section>

      <section className="card space-y-4">
        <h2 className="font-bold">Checks</h2>
        <label className="block">
          <span className="text-sm font-semibold">Similarity threshold: {s.similarity_threshold.toFixed(2)}</span>
          <p className="text-xs text-ink-muted">
            A claim with no current passage above this score is labelled “Unable to verify” without calling the LLM.
          </p>
          <input
            type="range"
            min={0.2}
            max={0.8}
            step={0.01}
            value={s.similarity_threshold}
            onChange={(e) => setS({ ...s, similarity_threshold: Number(e.target.value) })}
            className="mt-2 w-full accent-brand"
          />
        </label>
        <label className="block">
          <span className="text-sm font-semibold">Max follow-up questions</span>
          <select
            className="input mt-1 w-32"
            value={s.max_followups}
            onChange={(e) => setS({ ...s, max_followups: Number(e.target.value) })}
          >
            {[0, 1, 2].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <button className="btn-primary" onClick={save}>
          Save settings
        </button>
        <button className="btn-secondary" onClick={runTest}>
          Test provider
        </button>
        {saved && <Badge tone="ok">Saved</Badge>}
        {test && (test.ok ? <Badge tone="ok">Provider OK</Badge> : <Badge tone="bad">Provider failed</Badge>)}
      </div>
      {test?.error && <p className="text-sm text-ink-muted">{test.error}</p>}
    </div>
  );
}
