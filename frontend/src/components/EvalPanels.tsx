// Admin dashboard panels for "proof it works": eval metrics and Trust Challenge results.
import { useState } from "react";
import { api, type EvalResults, type TrustSummary } from "../api";
import { colors } from "../theme";
import { BarList, ChartCard, SimpleTable, StatTile } from "./charts";
import { Badge, EmptyState, ErrorNote } from "./ui";

const pct = (x: number | null | undefined) => (x == null ? "—" : `${Math.round(x * 100)}%`);
const TYPE_NAMES: Record<string, string> = {
  correct: "Correct answers",
  missing_exception: "Missing exceptions",
  outdated_source: "Outdated sources",
  no_evidence: "No evidence",
};

export function EvalPanel({ initial }: { initial: EvalResults | null }) {
  const [results, setResults] = useState<EvalResults | null>(initial);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    setRunning(true);
    setError("");
    try {
      setResults(await api.post<EvalResults>("/api/admin/eval/run"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <section className="card space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">Evaluation</h2>
          <p className="text-xs text-ink-muted">
            40 labelled answers checked by Q AI directly (python -m app.eval), plus the retry study on real questions.
          </p>
        </div>
        <button className="btn-secondary" onClick={run} disabled={running}>
          {running ? "Running eval…" : "Run eval now"}
        </button>
      </div>
      {error && <ErrorNote message={error} />}
      {!results ? (
        <EmptyState title="No eval results yet">Run “python -m app.eval” or press “Run eval now”.</EmptyState>
      ) : (
        <>
          <p className="text-xs text-ink-muted">
            Last run {new Date(results.run_at).toLocaleString()} · provider: {results.provider} · {results.cases} cases
          </p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatTile label="Verdict accuracy" value={pct(results.verdict_accuracy)} />
            <StatTile
              label="Missed errors"
              value={`${results.missed_errors.count} / ${results.missed_errors.of}`}
              note="bad answers shown as Green"
            />
            <StatTile
              label="False flags"
              value={`${results.false_flags.count} / ${results.false_flags.of}`}
              note="correct answers flagged"
            />
            <StatTile
              label="Fixed by one retry"
              value={`${results.retry.fixed} / ${results.retry.amber_first}`}
              note="Amber → Green, full workflow"
            />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard
              title="Accuracy per check"
              subtitle="Did the check flag exactly the cases it should?"
              table={
                <SimpleTable
                  head={["Check", "Accuracy"]}
                  rows={[
                    ["A – rules and timeframes", pct(results.per_check_accuracy.A)],
                    ["B – sources", pct(results.per_check_accuracy.B)],
                    ["C – intent", pct(results.per_check_accuracy.C)],
                  ]}
                />
              }
            >
              <BarList
                valueLabel="Accuracy %"
                data={[
                  { label: "A – rules", value: Math.round(results.per_check_accuracy.A * 100) },
                  { label: "B – sources", value: Math.round(results.per_check_accuracy.B * 100) },
                  { label: "C – intent", value: Math.round(results.per_check_accuracy.C * 100) },
                ]}
              />
            </ChartCard>
            <div className="space-y-2">
              <h3 className="font-bold">By case type</h3>
              <SimpleTable
                head={["Type", "Right verdict"]}
                rows={Object.entries(results.by_type).map(([t, v]) => [TYPE_NAMES[t] ?? t, `${v.verdict_ok} / ${v.cases}`])}
              />
              <p className="text-xs text-ink-muted">Expected flags found: {pct(results.flag_recall)}</p>
            </div>
          </div>
          <details className="rounded-xl border border-line p-4">
            <summary className="cursor-pointer text-sm font-bold">All {results.rows.length} cases</summary>
            <div className="mt-3 max-h-96 overflow-auto">
              <SimpleTable
                head={["Case", "Expected", "Got", "Flags missed"]}
                rows={results.rows.map((r) => [
                  r.id,
                  r.expected_verdict,
                  `${r.got_verdict}${r.verdict_ok ? "" : "  ✕"}`,
                  r.missing_flags.join(", ") || "—",
                ])}
              />
            </div>
          </details>
        </>
      )}
    </section>
  );
}

export function TrustPanel({ summary }: { summary: TrustSummary | null }) {
  return (
    <section className="card space-y-3">
      <div>
        <h2 className="text-lg font-bold">Trust Challenge results</h2>
        <p className="text-xs text-ink-muted">
          How often participants made the right call: Round A (answer text only) vs Round B (with Q AI's evidence view).
        </p>
      </div>
      {!summary || summary.participants === 0 ? (
        <EmptyState title="No participants yet">Share the Trust Challenge page to collect results.</EmptyState>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 text-sm">
            <Badge tone="muted">{summary.participants} participant(s)</Badge>
            <Badge tone="muted">{summary.completed} completed both rounds</Badge>
          </div>
          <ChartCard
            title="Right calls"
            table={
              <SimpleTable
                head={["Round", "Correct", "Answers", "Accuracy"]}
                rows={(["A", "B"] as const).map((r) => [
                  r === "A" ? "A – text only" : "B – with evidence",
                  summary[r].correct,
                  summary[r].answers,
                  pct(summary[r].accuracy),
                ])}
              />
            }
          >
            <BarList
              color={colors.brand.DEFAULT}
              valueLabel="Accuracy %"
              data={[
                { label: "A – text only", value: Math.round((summary.A.accuracy ?? 0) * 100) },
                { label: "B – with evidence", value: Math.round((summary.B.accuracy ?? 0) * 100) },
              ]}
            />
          </ChartCard>
        </>
      )}
    </section>
  );
}
