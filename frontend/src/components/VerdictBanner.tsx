// The verdict banner: always a word (Green / Amber / Red) plus an explanation, never colour alone.
import type { Verdict } from "../api";
import { VERDICTS } from "./labels";

const STYLES = {
  ok: "border-ok/40 bg-ok-tint text-ok",
  warn: "border-warn/40 bg-warn-tint text-warn",
  bad: "border-bad/40 bg-bad-tint text-brand-dark",
  muted: "border-line bg-muted-tint text-ink-muted",
  brand: "border-brand/30 bg-brand-tint text-brand-dark",
};

const ICONS = { Green: "✓", Amber: "!", Red: "✕" };

export default function VerdictBanner({
  verdict,
  inReview,
  corrected = false,
  reviewed = false,
  retrying = false,
}: {
  verdict: Verdict;
  inReview: boolean;
  corrected?: boolean;
  reviewed?: boolean;
  retrying?: boolean;
}) {
  const v = VERDICTS[verdict];
  let title = v.title;
  let text = inReview && verdict !== "Red" ? "A reviewer will check this answer." : v.text;
  if (verdict === "Amber" && inReview) title = "Amber: sent for review – check before acting";
  if (verdict === "Green" && corrected) title = "Green: corrected answer – checks passed";
  if (retrying) {
    title = `${verdict}: not good enough yet – Q AI asks OCBC AI to try again`;
    text = "Some sentences could not be verified. OCBC AI gets one more try below.";
  }
  if (reviewed) {
    title = `${verdict}: reviewed by a person – see their decision below`;
    text = "Q AI flagged OCBC AI's answer, and a reviewer has now checked it.";
  }
  return (
    <div className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${STYLES[v.tone]}`} role="status">
      <span
        className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-current text-sm font-bold"
        aria-hidden="true"
      >
        {ICONS[verdict]}
      </span>
      <div>
        <p className="font-bold">{title}</p>
        <p className="text-sm text-ink">{text}</p>
      </div>
    </div>
  );
}
