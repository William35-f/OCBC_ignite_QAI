// Small shared UI pieces: badges, loading and empty/error states.
import type { ReactNode } from "react";

type Tone = "ok" | "warn" | "bad" | "muted" | "brand";

const TONES: Record<Tone, string> = {
  ok: "bg-ok-tint text-ok border-ok/30",
  warn: "bg-warn-tint text-warn border-warn/30",
  bad: "bg-bad-tint text-bad border-bad/30",
  muted: "bg-muted-tint text-ink-muted border-line",
  brand: "bg-brand-tint text-brand-dark border-brand/20",
};

/** A pill that always carries a text label (colour is never the only signal). */
export function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-ink-muted" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-brand" aria-hidden="true" />
      {label}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-bad/30 bg-bad-tint px-4 py-3 text-sm text-brand-dark" role="alert">
      <strong>Something went wrong:</strong> {message}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-line px-6 py-10 text-center">
      <p className="font-semibold text-ink">{title}</p>
      {children && <div className="mt-1 text-sm text-ink-muted">{children}</div>}
    </div>
  );
}

