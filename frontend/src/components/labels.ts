// How each claim label, verdict and part status looks. Every style is paired with text.

export type Tone = "ok" | "warn" | "bad" | "muted" | "brand";

export const LABELS: Record<string, { tone: Tone; mark: string; help: string }> = {
  Supported: {
    tone: "ok",
    mark: "bg-ok-tint decoration-ok",
    help: "A current procedure states this.",
  },
  "Partly supported": {
    tone: "warn",
    mark: "bg-warn-tint decoration-warn",
    help: "Only part of this sentence is in a current procedure.",
  },
  Unsupported: {
    tone: "warn",
    mark: "bg-warn-tint decoration-warn decoration-dashed",
    help: "Current procedures on this topic do not say this.",
  },
  Contradicted: {
    tone: "bad",
    mark: "bg-bad-tint decoration-bad",
    help: "A current procedure says something different.",
  },
  "Unable to verify": {
    tone: "muted",
    mark: "bg-muted-tint decoration-ink-muted decoration-dashed",
    help: "No approved source covers this sentence.",
  },
  "Not a claim": { tone: "muted", mark: "", help: "Not a factual statement, so not checked." },
};

export const VERDICTS = {
  Green: { tone: "ok" as Tone, title: "Green: checks passed", text: "Every sentence is supported by a current procedure." },
  Amber: {
    tone: "warn" as Tone,
    title: "Amber: needs a closer look",
    text: "Some sentences could not be verified against current procedures.",
  },
  Red: {
    tone: "bad" as Tone,
    title: "Red: pending review – do not process yet",
    text: "Q AI found a serious problem. A reviewer will check this answer.",
  },
};

export const PART_STATUS: Record<string, { tone: Tone; text: string }> = {
  answered: { tone: "ok", text: "Answered" },
  partly: { tone: "warn", text: "Partly answered" },
  not_answered: { tone: "bad", text: "Not answered" },
};

export const SEVERITY: Record<string, { tone: Tone; text: string }> = {
  critical: { tone: "bad", text: "Critical" },
  warning: { tone: "warn", text: "Check" },
  info: { tone: "muted", text: "Note" },
};

export const CHECK_NAMES: Record<string, string> = {
  A: "Rules",
  B: "Sources",
  C: "Intent",
};

export const FLAG_NAMES: Record<string, string> = {
  outdated_source: "Outdated source",
  quote_mismatch: "Quote does not match",
  no_citation: "No citation",
  citation_not_found: "Citation not found",
  figure_mismatch: "Figure not in source",
  contradicted: "Contradicted claim",
  missing_exception: "Missing exception",
  partly_supported: "Partly supported",
  unsupported: "Unsupported claim",
  unable_to_verify: "Unable to verify",
  conflict_older_source: "Conflicting source",
  conflict_note: "Known conflict (note)",
  part_partly_answered: "Part partly answered",
  part_not_answered: "Part not answered",
};

export const QUEUE_REASONS: Record<string, string> = {
  red: "Red verdict",
  amber_after_retry: "Amber after retry",
  reported: "Reported by employee",
};

export const REVIEW_STATUS: Record<string, { tone: Tone; text: string }> = {
  pending: { tone: "warn", text: "Pending" },
  approved: { tone: "ok", text: "Approved" },
  corrected: { tone: "ok", text: "Corrected" },
  rejected: { tone: "bad", text: "Rejected" },
};

export const RULE_NAMES: Record<string, string> = {
  citation_exists: "Cites a source",
  source_current: "Source is current",
  figures_match: "Figures match source",
  quotes_match: "Quotes match source",
};
