// One question in the chat thread: the prompt check, follow-up chips, progress and OCBC AI's answer.
import { useEffect, useState } from "react";
import { api, type Run } from "../api";
import AnswerView from "./AnswerView";
import { Badge, ErrorNote } from "./ui";

// Workflow steps in order, as the backend names them in run.stage
export const STAGES = [
  "Checking your question",
  "OCBC AI is answering",
  "Checking rules, sources and intent",
  "Deciding verdict",
];
// Only shown when an Amber answer gets its one retry (Step 5b)
const RETRY_STAGES = ["Self-correcting: OCBC AI tries once more", "Re-checking the corrected answer"];

const POLL_MS = 400;

export default function RunCard({ initial }: { initial: Run }) {
  const [run, setRun] = useState<Run>(initial);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  // Refresh once on mount (the thread is restored from session storage)
  useEffect(() => {
    api.get<Run>(`/api/chat/runs/${initial.id}`).then(setRun).catch(() => {});
  }, [initial.id]);

  // Poll while OCBC AI and Q AI are working
  useEffect(() => {
    if (run.status !== "running" && run.status !== "checking_prompt") return;
    const t = setTimeout(() => {
      api.get<Run>(`/api/chat/runs/${run.id}`).then(setRun).catch((e) => setError(e.message));
    }, POLL_MS);
    return () => clearTimeout(t);
  }, [run]);

  const choose = async (name: string, option: string) => {
    setSending(true);
    try {
      setRun(await api.post<Run>(`/api/chat/runs/${run.id}/details`, { details: { [name]: option } }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  };

  const pc = run.prompt_check;
  const given = Object.entries(run.details).filter(([k]) => !(pc?.known_details ?? {})[k]);

  return (
    <article className="space-y-3">
      {/* Employee's question */}
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-ink px-4 py-3 text-sm text-surface">
          {run.question}
          {given.length > 0 && (
            <div className="mt-1 text-xs opacity-80">
              {given.map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`).join(" · ")}
            </div>
          )}
        </div>
      </div>

      {/* Q AI prompt check */}
      {pc && (
        <div className="card space-y-3 border-l-4 border-l-brand py-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wide text-brand-dark">Q AI · prompt check</span>
            {pc.matched_document && <Badge tone="muted">Topic: {pc.topic.replace(/_/g, " ")}</Badge>}
          </div>

          {pc.correction_notes.map((note) => (
            <div key={note} className="rounded-xl border border-warn/40 bg-warn-tint px-3 py-2 text-sm text-ink" role="note">
              <strong className="text-warn">Correction: </strong>
              {note.replace(/^Note:\s*/, "")}
            </div>
          ))}

          <p className="text-sm text-ink-muted">
            <span className="font-semibold text-ink">Searched for:</span> “{pc.search_query}”
          </p>

          {pc.parts.length > 1 && (
            <div className="text-sm">
              <span className="font-semibold">Your question has {pc.parts.length} parts. Q AI will check each is answered:</span>
              <ol className="mt-1 list-decimal space-y-0.5 pl-5 text-ink-muted">
                {pc.parts.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ol>
            </div>
          )}

          {run.status === "needs_details" &&
            pc.missing_details.map((f) => (
              <div key={f.name} className="rounded-xl bg-brand-tint px-3 py-3">
                <p className="text-sm font-semibold">{f.question}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {f.options.map((o) => (
                    <button key={o} disabled={sending} onClick={() => choose(f.name, o)} className="btn-secondary rounded-full">
                      {o}
                    </button>
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}

      {/* Progress */}
      {(run.status === "running" || run.status === "checking_prompt") && <Progress stage={run.stage} />}

      {/* OCBC AI answer with Q AI's evidence view */}
      {run.status === "done" && run.original_checks && <AnswerView run={run} onChange={setRun} />}

      {run.status === "error" && <ErrorNote message={run.error ?? "The workflow failed."} />}
      {error && <ErrorNote message={error} />}
    </article>
  );
}

function Progress({ stage }: { stage: string }) {
  // The retry steps only appear once an Amber answer is being retried
  const steps = RETRY_STAGES.includes(stage) ? [...STAGES, ...RETRY_STAGES] : STAGES;
  // "Queued" (prompt check done, OCBC AI not started yet) counts as the second step
  const found = steps.indexOf(stage);
  const current = found === -1 ? 1 : found;
  return (
    <div className="card py-4" role="status" aria-live="polite">
      <p className="mb-2 text-sm font-semibold">Checking…</p>
      <ol className="space-y-1.5 text-sm">
        {steps.map((s, i) => {
          const state = current === -1 ? "todo" : i < current ? "done" : i === current ? "now" : "todo";
          return (
            <li key={s} className="flex items-center gap-2">
              {state === "done" && <span className="w-14 text-xs font-semibold text-ok">Done</span>}
              {state === "now" && (
                <span className="flex w-14 items-center gap-1 text-xs font-semibold text-brand-dark">
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-line border-t-brand" aria-hidden="true" />
                  Now
                </span>
              )}
              {state === "todo" && <span className="w-14 text-xs text-ink-muted">Waiting</span>}
              <span className={state === "todo" ? "text-ink-muted" : "text-ink"}>
                {s}
                {s === "Checking rules, sources and intent" && (
                  <span className="block text-xs text-ink-muted">A rules · B sources · C intent, in parallel</span>
                )}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
