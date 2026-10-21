// Admin dashboard (Step 8): what is going wrong, why, and the fixes - verified by a retest.
import { useCallback, useEffect, useState } from "react";
import { api, type ActivityRow, type Dashboard, type RetestResult, type Suggestion } from "../api";
import { BarList, ChartCard, SimpleTable, StatTile, VerdictChart } from "../components/charts";
import { FLAG_NAMES } from "../components/labels";
import { Badge, EmptyState, ErrorNote, Spinner } from "../components/ui";
import { colors } from "../theme";

const SUGGESTION_STATUS = {
  open: { tone: "warn" as const, text: "Open" },
  applied: { tone: "brand" as const, text: "Applied – run retest to verify" },
  done: { tone: "ok" as const, text: "Done – retest passed" },
};

export default function Admin() {
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [retest, setRetest] = useState<RetestResult | null>(null);
  const [activity, setActivity] = useState<ActivityRow[]>([]);
  const [busy, setBusy] = useState<string>("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [d, s, r, a] = await Promise.all([
        api.get<Dashboard>("/api/admin/dashboard"),
        api.get<Suggestion[]>("/api/admin/suggestions"),
        api.get<RetestResult | null>("/api/admin/retest/latest"),
        api.get<ActivityRow[]>("/api/admin/activity"),
      ]);
      setDash(d);
      setSuggestions(s);
      setRetest(r);
      setActivity(a);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const applyFix = async (s: Suggestion) => {
    setBusy(s.id);
    setError("");
    try {
      await api.post("/api/admin/fixes/retire", { doc_id: s.target });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  };

  const runRetest = async () => {
    setBusy("retest");
    setError("");
    try {
      setRetest(await api.post<RetestResult>("/api/admin/retest"));
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  };

  if (!dash) return error ? <ErrorNote message={error} /> : <Spinner label="Loading dashboard…" />;
  const t = dash.totals;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Dashboard</h1>
        <p className="muted">Every question is logged. Here is what goes wrong, where it comes from, and how to fix it.</p>
      </div>
      {error && <ErrorNote message={error} />}

      {/* Headline numbers */}
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
        <StatTile label="Answers checked" value={t.answers} />
        <StatTile label="Green" value={t.green} note="shown to the employee" />
        <StatTile label="Amber" value={t.amber} note="after one retry" />
        <StatTile label="Red" value={t.red} note="sent to review" />
        <StatTile label="Fixed by retry" value={`${t.fixed_by_retry} / ${t.retried}`} note="Amber → Green" />
        <StatTile label="Pending reviews" value={t.pending_reviews} note={`${t.golden} in golden set`} />
      </section>

      {/* Fix suggestions + retest */}
      <section className="grid gap-4 xl:grid-cols-5">
        <div className="card space-y-3 xl:col-span-3">
          <div>
            <h2 className="text-lg font-bold">Fix suggestions</h2>
            <p className="text-xs text-ink-muted">From fixed templates, based on the logged flags. Not AI-generated.</p>
          </div>
          {suggestions.length === 0 ? (
            <EmptyState title="No suggestions yet">They appear once answers have been checked.</EmptyState>
          ) : (
            <ul className="space-y-3">
              {suggestions.map((s) => (
                <li key={s.id} className="rounded-xl border border-line p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <p className="font-semibold">{s.title}</p>
                    <Badge tone={SUGGESTION_STATUS[s.status].tone}>{SUGGESTION_STATUS[s.status].text}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-ink-muted">{s.evidence}</p>
                  {s.kind === "retire_document" && s.can_apply && (
                    <button className="btn-primary mt-3" disabled={busy !== ""} onClick={() => applyFix(s)}>
                      {busy === s.id ? "Applying…" : "Apply fix"}
                    </button>
                  )}
                  {s.kind !== "retire_document" && (
                    <p className="mt-2 text-xs text-ink-muted">Needs the document owner: no automatic fix.</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card space-y-3 xl:col-span-2">
          <div>
            <h2 className="text-lg font-bold">Retest</h2>
            <p className="text-xs text-ink-muted">
              Reruns the golden set and the held-out questions through the full workflow. A fix only counts as done once
              the retest passes.
            </p>
          </div>
          <button className="btn-primary" disabled={busy !== ""} onClick={runRetest}>
            {busy === "retest" ? "Running retest…" : "Run retest"}
          </button>
          {retest ? (
            <div className="space-y-2">
              <p className="flex flex-wrap items-center gap-2 text-sm">
                <Badge tone={retest.passed ? "ok" : "bad"}>{retest.passed ? "Passed" : "Failed"}</Badge>
                {retest.passed_count} of {retest.total} cases passed ·{" "}
                <span className="text-ink-muted">{new Date(retest.created_at).toLocaleString()}</span>
              </p>
              <ul className="max-h-80 space-y-1.5 overflow-y-auto pr-1 text-sm">
                {retest.results.map((r, i) => (
                  <li key={i} className="rounded-lg border border-line px-3 py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={r.passed ? "ok" : "bad"}>{r.passed ? "Pass" : "Fail"}</Badge>
                      <Badge tone="muted">{r.kind}</Badge>
                      <span className="text-xs text-ink-muted">
                        expected {r.expected}, got {r.got ?? "no answer"}
                      </span>
                    </div>
                    <p className="mt-1">{r.question}</p>
                    {!r.passed && r.reason && <p className="text-xs text-ink-muted">{r.reason}</p>}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-ink-muted">No retest has been run yet.</p>
          )}
        </div>
      </section>

      {/* Charts */}
      <section className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Verdicts over time"
          subtitle="Final verdict per answer, by day"
          table={
            <SimpleTable
              head={["Day", "Green", "Amber", "Red"]}
              rows={dash.verdicts_over_time.map((d) => [d.day, d.Green, d.Amber, d.Red])}
            />
          }
        >
          {dash.verdicts_over_time.length ? (
            <VerdictChart data={dash.verdicts_over_time} />
          ) : (
            <EmptyState title="No answers yet" />
          )}
        </ChartCard>

        <ChartCard
          title="Most common flags"
          subtitle="On OCBC AI's first answers"
          table={
            <SimpleTable head={["Flag", "Answers"]} rows={dash.flag_counts.map((f) => [FLAG_NAMES[f.type] ?? f.type, f.count])} />
          }
        >
          {dash.flag_counts.length ? (
            <BarList data={dash.flag_counts.map((f) => ({ label: FLAG_NAMES[f.type] ?? f.type, value: f.count }))} />
          ) : (
            <EmptyState title="No flags yet" />
          )}
        </ChartCard>

        <ChartCard
          title="Topics that fail most"
          subtitle="Answers not Green, by topic"
          table={
            <SimpleTable
              head={["Topic", "Not Green", "Total"]}
              rows={dash.topic_failures.map((x) => [x.topic.replace(/_/g, " "), x.failed, x.total])}
            />
          }
        >
          {dash.topic_failures.some((x) => x.failed > 0) ? (
            <BarList
              color={colors.brand.dark}
              valueLabel="Not Green"
              data={dash.topic_failures.filter((x) => x.failed > 0).map((x) => ({ label: x.topic.replace(/_/g, " "), value: x.failed }))}
            />
          ) : (
            <EmptyState title="No failing topics" />
          )}
        </ChartCard>

        <section className="card space-y-3">
          <h3 className="font-bold">Reviewer decisions</h3>
          <div className="grid grid-cols-3 gap-3">
            <StatTile label="Approved" value={dash.reviewer_decisions.approved} />
            <StatTile label="Corrected" value={dash.reviewer_decisions.corrected} />
            <StatTile label="Rejected" value={dash.reviewer_decisions.rejected} />
          </div>
          <p className="text-sm text-ink-muted">
            Employees used {t.used} answer(s) and reported {t.reported}.
          </p>
        </section>
      </section>

      {/* Which documents cause which errors */}
      <section className="card space-y-3">
        <h2 className="text-lg font-bold">Documents behind the errors</h2>
        {dash.doc_errors.length === 0 ? (
          <EmptyState title="No document-linked errors yet" />
        ) : (
          <div className="overflow-x-auto">
            <SimpleTable
              head={["Document", "Errors", "Total"]}
              rows={dash.doc_errors.map((d) => [
                d.doc_label,
                Object.entries(d.errors)
                  .map(([k, v]) => `${FLAG_NAMES[k] ?? k} × ${v}`)
                  .join(", "),
                d.total,
              ])}
            />
          </div>
        )}
      </section>

      <div id="eval-slot" />

      {/* Audit log */}
      <section className="card space-y-3">
        <h2 className="text-lg font-bold">Activity log</h2>
        <p className="text-xs text-ink-muted">Latest events. Every step of every question is recorded with a timestamp.</p>
        {activity.length === 0 ? (
          <EmptyState title="Nothing logged yet" />
        ) : (
          <div className="max-h-96 overflow-auto">
            <SimpleTable
              head={["Time", "Event", "By", "Question"]}
              rows={activity.map((a) => [
                new Date(a.at).toLocaleTimeString(),
                a.event.replace(/_/g, " "),
                a.actor,
                a.question ? (a.question.length > 70 ? a.question.slice(0, 67) + "…" : a.question) : "—",
              ])}
            />
          </div>
        )}
      </section>
    </div>
  );
}
