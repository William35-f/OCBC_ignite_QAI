// Step 5b - "What changed": a simple sentence diff between OCBC AI's first answer and its one retry.
import type { Run } from "../api";
import { Badge } from "./ui";
import { VERDICTS } from "./labels";

export default function WhatChanged({ run }: { run: Run }) {
  if (!run.retried || run.what_changed.length === 0) return null;
  const before = run.original_verdict ? VERDICTS[run.original_verdict] : null;
  const after = run.retry_verdict ? VERDICTS[run.retry_verdict] : null;

  return (
    <details className="rounded-xl border border-line p-4" open>
      <summary className="cursor-pointer text-sm font-bold">What changed</summary>
      <div className="mt-3 space-y-3 text-sm">
        <p className="text-ink-muted">
          Q AI found problems in OCBC AI's first answer and asked it to answer once more, using only the current
          procedures. Q AI did not edit the answer itself. The first answer is kept on record.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {before && <Badge tone={before.tone}>First answer: {run.original_verdict}</Badge>}
          <span aria-hidden="true">→</span>
          {after && <Badge tone={after.tone}>After one retry: {run.retry_verdict}</Badge>}
        </div>
        <ul className="space-y-1.5">
          {run.what_changed.map((d, i) => (
            <li key={i} className="flex gap-2">
              <span className="w-20 shrink-0">
                {d.type === "removed" && <Badge tone="bad">Removed</Badge>}
                {d.type === "added" && <Badge tone="ok">Added</Badge>}
                {d.type === "same" && <Badge tone="muted">Kept</Badge>}
              </span>
              <span className={d.type === "removed" ? "text-ink-muted line-through" : d.type === "same" ? "text-ink-muted" : ""}>
                {d.text}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}
