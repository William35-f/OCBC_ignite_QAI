// One question in the chat thread, in the order things happen:
//   You -> Q AI checks the question -> OCBC AI's exact answer -> Q AI checks the answer
//   (-> Q AI feedback -> OCBC AI's second answer -> Q AI checks it, for an Amber retry)
import { useEffect, useState } from "react";
import { api, type Run } from "../api";
import AnswerView from "./AnswerView";
import { AgentAnswer, LaneHeader, RetryFeedback } from "./Lanes";
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
// Who does each step, shown next to it in the progress list
const WHO: Record<string, string> = {
  "Checking your question": "Q AI",
  "OCBC AI is answering": "OCBC AI",
  "Checking rules, sources and intent": "Q AI",
  "Deciding verdict": "Q AI",
  "Self-correcting: OCBC AI tries once more": "OCBC AI",
  "Re-checking the corrected answer": "Q AI",
};

const POLL_MS = 400;
const REVIEW_POLL_MS = 5000;

export default function RunCard({ initial }: { initial: Run }) {
  const [run, setRun] = useState<Run>(initial);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  // Refresh once on mount (the thread is restored from session storage)
  useEffect(() => {
    api
      .get<Run>(`/api/chat/runs/${initial.id}`)
      .then(setRun)
      .catch((e) =>
        setError(
          e.message === "Run not found"
            ? "This question is no longer on record (the demo was reset). Use “Clear chat”."
            : e.message,
        ),
      );
  }, [initial.id]);

  // Poll while OCBC AI and Q AI are working, then slowly while a reviewer has it
  useEffect(() => {
    const working = run.status === "running" || run.status === "checking_prompt";
    const awaitingReview = run.status === "done" && (run.review?.status === "pending" ||
      (run.routed_to === "review" && !run.review));
    if (!working && !awaitingReview) return;
    const t = setTimeout(() => {
      api.get<Run>(`/api/chat/runs/${run.id}`).then(setRun).catch((e) => setError(e.message));
    }, working ? POLL_MS : REVIEW_POLL_MS);
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
      {/* The employee's question */}
      <p className="text-right text-xs font-bold uppercase tracking-wide text-ink-muted">You</p>
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

      {/* Step 1 - Q AI checks the question (before OCBC AI answers) */}
      {pc && (
        <div className="card space-y-3 border-l-4 border-l-brand py-4">
          <LaneHeader
            who="qai"
            step={1}
            title="checks your question before OCBC AI answers"
            extra={pc.matched_document && <Badge tone="muted">Topic: {pc.topic.replace(/_/g, " ")}</Badge>}
          />

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

      {/* Step 2 - OCBC AI's exact answer, as soon as it exists */}
      {run.original_answer && (
        <AgentAnswer
          step={2}
          title={run.retried ? "first answer" : "answers your question"}
          text={run.original_answer}
          checked={Boolean(run.original_checks)}
        />
      )}

      {/* Step 3 - Q AI checks that answer */}
      {run.original_checks && (run.retried || run.status === "done") && (
        <AnswerView
          checks={run.original_checks}
          step={3}
          title="checks OCBC AI's answer"
          mode={run.retried ? "retrying" : "final"}
          run={run}
          onChange={setRun}
        />
      )}

      {/* Steps 4-6 - one retry for an Amber answer */}
      {run.retried && run.retry_feedback && <RetryFeedback step={4} feedback={run.retry_feedback} />}
      {run.retry_answer && (
        <AgentAnswer
          step={5}
          title="answers again after Q AI's feedback"
          text={run.retry_answer}
          checked={Boolean(run.retry_checks)}
        />
      )}
      {run.retry_checks && run.status === "done" && (
        <AnswerView
          checks={run.retry_checks}
          step={6}
          title="checks OCBC AI's new answer"
          mode="final"
          run={run}
          onChange={setRun}
        />
      )}

      {/* Progress while OCBC AI or Q AI is working */}
      {(run.status === "running" || run.status === "checking_prompt") && <Progress stage={run.stage} />}

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
                <span className={`mr-1.5 text-xs font-bold ${WHO[s] === "Q AI" ? "text-brand-dark" : "text-ink"}`}>
                  {WHO[s]}
                </span>
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
