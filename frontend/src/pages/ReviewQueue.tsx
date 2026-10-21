// Reviewer: one queue for Red answers, Amber answers that failed their retry, and reported answers.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type GoldenRow, type QueueRow } from "../api";
import { FLAG_NAMES, QUEUE_REASONS, REVIEW_STATUS, VERDICTS } from "../components/labels";
import { Badge, EmptyState, ErrorNote, Spinner } from "../components/ui";

type Tab = "pending" | "all" | "golden";

export function timeAgo(iso: string): string {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  return new Date(iso).toLocaleDateString();
}

export default function ReviewQueue() {
  const [tab, setTab] = useState<Tab>("pending");
  const [rows, setRows] = useState<QueueRow[] | null>(null);
  const [golden, setGolden] = useState<GoldenRow[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    if (tab === "golden") {
      api.get<GoldenRow[]>("/api/review/golden").then(setGolden).catch((e) => setError(e.message));
    } else {
      setRows(null);
      api.get<QueueRow[]>(`/api/review/queue?status=${tab}`).then(setRows).catch((e) => setError(e.message));
    }
  }, [tab]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="page-title">Review queue</h1>
        <p className="muted">Answers Q AI would not show as trustworthy, plus answers employees reported.</p>
      </div>

      <div className="flex gap-1 border-b border-line" role="tablist">
        {(
          [
            ["pending", "Pending"],
            ["all", "All"],
            ["golden", "Golden set"],
          ] as [Tab, string][]
        ).map(([t, label]) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-semibold ${
              tab === t ? "border-brand text-brand-dark" : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <ErrorNote message={error} />}

      {tab !== "golden" && !rows && !error && <Spinner />}
      {tab !== "golden" && rows && rows.length === 0 && (
        <EmptyState title={tab === "pending" ? "Nothing waiting for review" : "No reviews yet"}>
          Red answers, Amber answers that fail their retry, and reported answers appear here.
        </EmptyState>
      )}
      {tab !== "golden" && rows && rows.length > 0 && (
        <div className="card overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="border-b border-line bg-canvas text-xs uppercase tracking-wide text-ink-muted">
                <tr>
                  <th className="px-4 py-3">Question</th>
                  <th className="px-4 py-3">Verdict</th>
                  <th className="px-4 py-3">Main flag</th>
                  <th className="px-4 py-3">Why here</th>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-b border-line last:border-0 hover:bg-canvas">
                    <td className="max-w-sm px-4 py-3">
                      <Link to={`/review/${r.id}`} className="font-semibold text-ink hover:text-brand-dark">
                        {r.question}
                      </Link>
                      <div className="text-xs text-ink-muted">Asked by {r.user_name}</div>
                    </td>
                    <td className="px-4 py-3">
                      {r.verdict && <Badge tone={VERDICTS[r.verdict].tone}>{r.verdict}</Badge>}
                    </td>
                    <td className="px-4 py-3">{FLAG_NAMES[r.main_flag] ?? "—"}</td>
                    <td className="px-4 py-3 text-ink-muted">{QUEUE_REASONS[r.queue_reason]}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-ink-muted">{timeAgo(r.created_at)}</td>
                    <td className="px-4 py-3">
                      <Badge tone={REVIEW_STATUS[r.status].tone}>{REVIEW_STATUS[r.status].text}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "golden" && !golden && !error && <Spinner />}
      {tab === "golden" && golden && golden.length === 0 && (
        <EmptyState title="The golden set is empty">Approved and corrected answers are saved here.</EmptyState>
      )}
      {tab === "golden" && golden && golden.length > 0 && (
        <ul className="space-y-3">
          {golden.map((g) => (
            <li key={g.id} className="card space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold">{g.question}</p>
                <span className="text-xs text-ink-muted">{new Date(g.created_at).toLocaleString()}</span>
              </div>
              {Object.keys(g.details).length > 0 && (
                <p className="text-xs text-ink-muted">
                  {Object.entries(g.details)
                    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
                    .join(" · ")}
                </p>
              )}
              <p className="rounded-lg bg-ok-tint px-3 py-2 text-sm">{g.correct_answer}</p>
              <div className="flex flex-wrap gap-1">
                {g.source_docs.map((d) => (
                  <Badge key={d} tone="muted">
                    {d}
                  </Badge>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
