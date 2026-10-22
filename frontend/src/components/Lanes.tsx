// Who is talking: the employee, OCBC AI (the simulated agent) or Q AI (the checking layer).
// Every block in the chat starts with one of these headers so the layers are never mixed up.
import type { ReactNode } from "react";
import { Badge } from "./ui";

export function QaiAvatar() {
  return (
    <span className="grid h-7 w-7 shrink-0 grid-cols-2 gap-0.5 rounded-lg bg-brand-tint p-1.5" aria-hidden="true">
      <span className="rounded-[2px] bg-brand" />
      <span className="rounded-[2px] bg-ink" />
      <span className="rounded-[2px] bg-ink" />
      <span className="rounded-[2px] bg-brand-dark" />
    </span>
  );
}

export function AgentAvatar() {
  return (
    <span
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ink text-[10px] font-bold text-surface"
      aria-hidden="true"
    >
      AI
    </span>
  );
}

/** "② OCBC AI · answers your question" */
export function LaneHeader({ who, step, title, extra }: { who: "qai" | "agent"; step?: number; title: string; extra?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {who === "qai" ? <QaiAvatar /> : <AgentAvatar />}
      <span className={`text-xs font-bold uppercase tracking-wide ${who === "qai" ? "text-brand-dark" : "text-ink"}`}>
        {who === "qai" ? "Q AI" : "OCBC AI (simulated agent)"}
      </span>
      <span className="text-xs text-ink-muted">
        {step !== undefined && <span className="font-semibold">Step {step} · </span>}
        {title}
      </span>
      {extra}
    </div>
  );
}

/** OCBC AI's answer exactly as it wrote it - nothing added, nothing removed. */
export function AgentAnswer({
  step,
  title,
  text,
  checked,
}: {
  step?: number;
  title: string;
  text: string;
  checked: boolean;
}) {
  return (
    <div className="space-y-2">
      <LaneHeader
        who="agent"
        step={step}
        title={title}
        extra={<Badge tone="muted">{checked ? "Exact answer, unedited" : "Exact answer – not checked yet"}</Badge>}
      />
      <div className="max-w-[92%] rounded-2xl rounded-tl-md border border-line bg-surface px-4 py-3 text-[15px] leading-relaxed shadow-sm">
        {text}
      </div>
    </div>
  );
}

/** Step 5b: what Q AI told OCBC AI before its one retry. */
export function RetryFeedback({ step, feedback }: { step?: number; feedback: string }) {
  return (
    <div className="card space-y-2 border-l-4 border-l-brand py-4">
      <LaneHeader who="qai" step={step} title="asks OCBC AI to answer once more" />
      <p className="text-sm">
        The answer was <strong>Amber</strong>, so Q AI sent OCBC AI its flags and the correct passages. Q AI never edits
        the answer itself.
      </p>
      <details className="text-sm">
        <summary className="cursor-pointer font-semibold text-ink-muted">Show the feedback Q AI sent</summary>
        <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-canvas p-3 font-sans text-xs text-ink-muted">{feedback}</pre>
      </details>
    </div>
  );
}
