// Reviewer detail: question, original answer, retry answer, correction side by side, with all flags and evidence.
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Checks, type ReviewItem, type Run } from "../api";
import { EvidencePanel, FlagList, HighlightedAnswer, PartsList, RuleSummary } from "../components/Evidence";
import { QUEUE_REASONS, REVIEW_STATUS, VERDICTS } from "../components/labels";
import { AgentAnswer, LaneHeader } from "../components/Lanes";
import { Badge, ErrorNote, Spinner } from "../components/ui";
import { USERS } from "../roles";

type Which = "original" | "retry";

export default function ReviewDetail() {
  const { id } = useParams();
  const [data, setData] = useState<{ item: ReviewItem; run: Run } | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<{ which: Which; index: number } | null>(null);
  const [correction, setCorrection] = useState("");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .get<{ item: ReviewItem; run: Run }>(`/api/review/items/${id}`)
      .then((d) => {
        setData(d);
        setCorrection(d.item.corrected_answer ?? d.run.final_answer ?? "");
      })
      .catch((e) => setError(e.message));
  }, [id]);

  const decide = async (action: "approve" | "correct" | "reject") => {
    setSaving(true);
    setError("");
    try {
      setData(
        await api.post(`/api/review/items/${id}/decide`, {
          action,
          reason,
          corrected_answer: action === "correct" ? correction : "",
          reviewer: USERS.reviewer.name,
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (!data) return error ? <ErrorNote message={error} /> : <Spinner />;
  const { item, run } = data;
  const pc = run.prompt_check;
  const pending = item.status === "pending";
  const sentenceOf = (which: Which) => {
    const checks = which === "original" ? run.original_checks : run.retry_checks;
    return selected?.which === which ? checks?.sentences.find((s) => s.index === selected.index) : undefined;
  };
  const selectedSentence = selected ? sentenceOf(selected.which) : undefined;

  return (
    <div className="space-y-5">
      <Link to="/review" className="text-sm font-medium text-ink-muted hover:text-ink">
        ← Back to queue
      </Link>

      {/* Question */}
      <section className="card space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="muted">{QUEUE_REASONS[item.queue_reason]}</Badge>
          <Badge tone={REVIEW_STATUS[item.status].tone}>{REVIEW_STATUS[item.status].text}</Badge>
          <span className="text-xs text-ink-muted">
            Asked by {run.user_name} · {new Date(run.created_at).toLocaleString()}
          </span>
        </div>
        <h1 className="text-xl font-bold">{run.question}</h1>
        {Object.keys(run.details).length > 0 && (
          <p className="text-sm text-ink-muted">
            Details:{" "}
            {Object.entries(run.details)
              .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
              .join(" · ")}
          </p>
        )}
        {pc && pc.correction_notes.length > 0 && (
          <p className="rounded-lg bg-warn-tint px-3 py-2 text-sm">
            <strong className="text-warn">Prompt check correction: </strong>
            {pc.correction_notes.join(" ")}
          </p>
        )}
        {run.employee_action === "used" && (
          <p className="rounded-lg bg-warn-tint px-3 py-2 text-sm">
            <strong>{run.user_name} already used this answer</strong>
            {run.employee_action_at && ` on ${new Date(run.employee_action_at).toLocaleString()}`}.{" "}
            {item.queue_reason === "used_after_amber" &&
              "It was Amber at first and Green only after OCBC AI's retry, so it needs a check after the fact. If it is wrong, correct it: the employee will see your correction."}
          </p>
        )}
        {run.report_reason && (
          <p className="rounded-lg bg-brand-tint px-3 py-2 text-sm">
            <strong>Employee's report:</strong> {run.report_reason}
          </p>
        )}
      </section>

      {/* Side by side: original / retry / correction */}
      <section className={`grid gap-4 ${run.retry_answer ? "xl:grid-cols-3" : "lg:grid-cols-2"}`}>
        <AnswerColumn
          title="original answer"
          text={run.original_answer}
          checks={run.original_checks}
          selected={selected?.which === "original" ? selected.index : null}
          onSelect={(i) => setSelected({ which: "original", index: i })}
        />
        {run.retry_answer && (
          <AnswerColumn
            title="retry answer, after Q AI's feedback"
            text={run.retry_answer}
            checks={run.retry_checks}
            selected={selected?.which === "retry" ? selected.index : null}
            onSelect={(i) => setSelected({ which: "retry", index: i })}
          />
        )}
        <div className="card space-y-2">
          <h2 className="text-xs font-bold uppercase tracking-wide text-ink">Reviewer · your correction</h2>
          <label htmlFor="correction" className="sr-only">
            Corrected answer
          </label>
          <textarea
            id="correction"
            className="input min-h-[160px]"
            value={correction}
            onChange={(e) => setCorrection(e.target.value)}
            disabled={!pending}
          />
          <p className="text-xs text-ink-muted">Edit the answer here, then choose “Correct”. Saved to the golden set.</p>
        </div>
      </section>

      {/* Evidence for the selected sentence */}
      <section className="card">
        <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-muted">Evidence</h2>
        <EvidencePanel sentence={selectedSentence} />
      </section>

      {/* Flags */}
      <section className={`grid gap-4 ${run.retry_checks ? "lg:grid-cols-2" : ""}`}>
        <FlagsCard title="Flags on the original answer" checks={run.original_checks} />
        {run.retry_checks && <FlagsCard title="Flags on the retry answer" checks={run.retry_checks} />}
      </section>

      {/* Decision */}
      <section className="card space-y-3">
        <h2 className="font-bold">Decision</h2>
        {pending ? (
          <>
            <label htmlFor="reason" className="block text-sm font-semibold">
              Reason (required)
            </label>
            <input
              id="reason"
              className="input"
              placeholder="e.g. Outdated source, missing exception"
              value={reason}
              maxLength={500}
              onChange={(e) => setReason(e.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={saving || reason.trim().length < 3} onClick={() => decide("approve")}>
                Approve
              </button>
              <button className="btn-primary" disabled={saving || reason.trim().length < 3} onClick={() => decide("correct")}>
                Correct
              </button>
              <button className="btn-secondary" disabled={saving || reason.trim().length < 3} onClick={() => decide("reject")}>
                Reject
              </button>
            </div>
            <p className="text-xs text-ink-muted">
              Approve keeps the answer as it is. Correct saves your edited answer. Both add it to the golden set.
            </p>
          </>
        ) : (
          <div className="space-y-2 text-sm">
            <p>
              <Badge tone={REVIEW_STATUS[item.status].tone}>{REVIEW_STATUS[item.status].text}</Badge> by {item.reviewer} on{" "}
              {item.decided_at && new Date(item.decided_at).toLocaleString()}
            </p>
            <p>
              <strong>Reason:</strong> {item.decision_reason}
            </p>
            {item.status !== "rejected" && <p className="text-ok">Saved to the golden set.</p>}
          </div>
        )}
        {error && <ErrorNote message={error} />}
      </section>
    </div>
  );
}

function AnswerColumn({
  title,
  text,
  checks,
  selected,
  onSelect,
}: {
  title: string;
  text: string | null;
  checks: Checks | null;
  selected: number | null;
  onSelect: (i: number) => void;
}) {
  return (
    <div className="card space-y-3">
      {text ? <AgentAnswer title={title} text={text} checked /> : <p className="text-sm text-ink-muted">No answer.</p>}
      {checks && (
        <div className="space-y-2 border-t border-line pt-3">
          <LaneHeader
            who="qai"
            title="labels on each sentence"
            extra={<Badge tone={VERDICTS[checks.verdict].tone}>{checks.verdict}</Badge>}
          />
          <HighlightedAnswer checks={checks} selected={selected} onSelect={onSelect} />
        </div>
      )}
    </div>
  );
}

function FlagsCard({ title, checks }: { title: string; checks: Checks | null }) {
  if (!checks) return null;
  return (
    <div className="card space-y-3">
      <h2 className="text-sm font-bold uppercase tracking-wide text-ink-muted">{title}</h2>
      <FlagList flags={checks.flags} />
      {checks.intent.length > 0 && <PartsList intent={checks.intent} />}
      <RuleSummary rule={checks.rule} />
    </div>
  );
}
