// Q AI's check of one OCBC AI answer: verdict, each sentence labelled, sources, reasons.
// mode "final"    - the answer the employee gets: review outcome + Use / Report buttons
// mode "retrying" - a first answer that was Amber: Q AI asked OCBC AI to try again
// mode "study"    - Trust Challenge round B: the check only, no buttons
import { useState } from "react";
import { api, type Checks, type Run } from "../api";
import { EvidencePanel, FlagList, HighlightedAnswer, PartsList, RuleSummary } from "./Evidence";
import { LaneHeader } from "./Lanes";
import { ErrorNote } from "./ui";
import VerdictBanner from "./VerdictBanner";
import WhatChanged from "./WhatChanged";

function firstProblem(checks: Checks): number | null {
  const order = ["Contradicted", "Unsupported", "Unable to verify", "Partly supported"];
  for (const label of order) {
    const s = checks.sentences.find((x) => x.label === label);
    if (s) return s.index;
  }
  return null;
}

export default function AnswerView({
  checks,
  step,
  title,
  mode,
  run,
  onChange,
}: {
  checks: Checks;
  step?: number;
  title: string;
  mode: "final" | "retrying" | "study";
  run?: Run;
  onChange?: (r: Run) => void;
}) {
  const [selected, setSelected] = useState<number | null>(() => firstProblem(checks));
  const sentence = checks.sentences.find((s) => s.index === selected);
  const review = run?.review;
  const decided = Boolean(review && review.status !== "pending");

  return (
    <div className="card space-y-4 border-l-4 border-l-brand">
      <LaneHeader who="qai" step={step} title={title} />
      <VerdictBanner
        verdict={checks.verdict}
        inReview={mode === "final" && run?.routed_to === "review"}
        corrected={mode === "final" && Boolean(run?.retried)}
        reviewed={mode === "final" && decided}
        retrying={mode === "retrying"}
      />

      {mode === "final" && run && <ReviewOutcome run={run} />}

      <div className="space-y-1">
        <p className="text-xs text-ink-muted">
          Q AI's labels on each sentence of OCBC AI's answer. Hover over or tap a sentence to see its source.
        </p>
        <HighlightedAnswer checks={checks} selected={selected} onSelect={setSelected} />
      </div>

      <div className="rounded-xl border border-line bg-surface p-4">
        <EvidencePanel sentence={sentence} />
      </div>

      <details className="rounded-xl border border-line p-4" open={checks.verdict !== "Green" && mode !== "retrying"}>
        <summary className="cursor-pointer text-sm font-bold">Why this verdict</summary>
        <div className="mt-3 space-y-4">
          <FlagList flags={checks.flags} />
          {checks.intent.length > 0 && (
            <div>
              <p className="mb-1 text-sm font-semibold">Each part of your question</p>
              <PartsList intent={checks.intent} />
            </div>
          )}
          <RuleSummary rule={checks.rule} />
        </div>
      </details>

      {mode === "final" && run?.retried && <WhatChanged run={run} />}
      {mode === "final" && run && onChange && <Actions run={run} onChange={onChange} />}
    </div>
  );
}

function ReviewOutcome({ run }: { run: Run }) {
  const review = run.review;
  if (!review || review.status === "pending") return null;
  return (
    <div
      className={`rounded-xl border px-4 py-3 text-sm ${
        review.status === "rejected" ? "border-bad/40 bg-bad-tint" : "border-ok/40 bg-ok-tint"
      }`}
      role="status"
    >
      <p className="font-bold">
        {review.status === "corrected" && `Reviewed by ${review.reviewer}: corrected answer below`}
        {review.status === "approved" && `Reviewed by ${review.reviewer}: approved`}
        {review.status === "rejected" && `Reviewed by ${review.reviewer}: rejected – do not use this answer`}
      </p>
      {review.corrected_answer && <p className="mt-2 text-[15px] leading-relaxed">{review.corrected_answer}</p>}
      <p className="mt-1 text-ink-muted">Reason: {review.decision_reason}</p>
    </div>
  );
}

/** Step 6 buttons: "Use answer" (logged) and "Report a problem". */
function Actions({ run, onChange }: { run: Run; onChange: (r: Run) => void }) {
  const [reporting, setReporting] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const review = run.review;
  const decided = review && review.status !== "pending";
  // "Use answer" waits for a reviewer, unless the reviewer approved or corrected it
  const inReview = (run.routed_to === "review" || review?.status === "pending") && !(decided && review.status !== "rejected");

  const act = async (path: "use" | "report") => {
    setError("");
    try {
      onChange(await api.post<Run>(`/api/chat/runs/${run.id}/${path}`, path === "report" ? { reason } : {}));
      setReporting(false);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-4">
        {run.employee_action === "used" && <p className="text-sm font-semibold text-ok">Logged: you used this answer.</p>}
        {run.employee_action === "reported" && (
          <p className="text-sm font-semibold text-brand-dark">Reported: sent to the review queue. Thank you.</p>
        )}
        {!run.employee_action && !reporting && (
          <>
            <button
              className="btn-primary"
              onClick={() => act("use")}
              disabled={inReview || review?.status === "rejected"}
              title={inReview ? "Wait for the reviewer before acting on this answer" : undefined}
            >
              {review?.status === "corrected" ? "Use corrected answer" : "Use answer"}
            </button>
            <button className="btn-secondary" onClick={() => setReporting(true)}>
              Report a problem
            </button>
            {inReview && <span className="text-xs text-ink-muted">“Use answer” is available after review.</span>}
          </>
        )}
        {reporting && (
          <form
            className="flex w-full flex-wrap gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              act("report");
            }}
          >
            <label htmlFor={`reason-${run.id}`} className="sr-only">
              Reason (optional)
            </label>
            <input
              id={`reason-${run.id}`}
              className="input min-w-0 flex-1"
              placeholder="What looks wrong? (optional, one line)"
              maxLength={300}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <button className="btn-primary">Send report</button>
            <button type="button" className="btn-secondary" onClick={() => setReporting(false)}>
              Cancel
            </button>
          </form>
        )}
      </div>
      {error && <ErrorNote message={error} />}
    </>
  );
}
