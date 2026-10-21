// Evidence view building blocks, shared by the Employee chat and the Review pages.
import type { Checks, Flag, SentenceView } from "../api";
import { CHECK_NAMES, LABELS, PART_STATUS, RULE_NAMES, SEVERITY } from "./labels";
import { Badge } from "./ui";

/** The answer, one highlighted sentence at a time. Hover, focus or click a sentence to see its sources. */
export function HighlightedAnswer({
  checks,
  selected,
  onSelect,
}: {
  checks: Checks;
  selected: number | null;
  onSelect: (i: number) => void;
}) {
  return (
    <p className="text-[15px] leading-8">
      {checks.sentences.map((s) => {
        const style = LABELS[s.label] ?? LABELS["Not a claim"];
        const cites = s.citations.filter((c) => c.own);
        if (s.label === "Not a claim") {
          return <span key={s.index}>{s.text} </span>;
        }
        return (
          <span key={s.index}>
            <button
              type="button"
              onMouseEnter={() => onSelect(s.index)}
              onFocus={() => onSelect(s.index)}
              onClick={() => onSelect(s.index)}
              aria-pressed={selected === s.index}
              aria-label={`${s.text} – ${s.label}. Show sources.`}
              className={`rounded px-0.5 text-left underline decoration-2 underline-offset-4 ${style.mark} ${
                selected === s.index ? "ring-2 ring-ink/30" : ""
              }`}
            >
              {s.text}
            </button>{" "}
            <Badge tone={style.tone}>{s.label}</Badge>{" "}
            {cites.length > 0 && (
              <span className="text-sm text-ink-muted">
                ({cites.map((c) => `${c.label}, ${c.sections.map((x) => `§${x}`).join(", ")}`).join("; ")}){" "}
              </span>
            )}
          </span>
        );
      })}
    </p>
  );
}

/** Exact source passage(s) for one sentence: document title, version, section, effective date. */
export function EvidencePanel({ sentence }: { sentence: SentenceView | undefined }) {
  if (!sentence) {
    return <p className="text-sm text-ink-muted">Hover over or tap a highlighted sentence to see its sources.</p>;
  }
  const style = LABELS[sentence.label] ?? LABELS["Not a claim"];
  const cited = sentence.citations.map((c) => `${c.label} ${c.sections.map((x) => `§${x}`).join(", ")}`);
  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={style.tone}>{sentence.label}</Badge>
        <span className="text-ink-muted">{style.help}</span>
      </div>
      <p className="font-medium">“{sentence.text}”</p>
      {sentence.reason && <p className="text-ink-muted">{sentence.reason}</p>}
      {sentence.correction && (
        <p className="rounded-lg bg-bad-tint px-3 py-2 text-brand-dark">{sentence.correction.replace(/^Note:\s*/, "Correct: ")}</p>
      )}
      {cited.length > 0 && (
        <p className="text-ink-muted">
          <span className="font-semibold text-ink">OCBC AI cited:</span> {cited.join("; ")}
          {sentence.citations.some((c) => c.status === "superseded") && (
            <>
              {" "}
              <Badge tone="bad">Superseded</Badge>
            </>
          )}
        </p>
      )}
      {sentence.evidence.length > 0 ? (
        <div className="space-y-2">
          <p className="font-semibold">Current procedure{sentence.evidence.length > 1 ? "s" : ""} checked against:</p>
          {sentence.evidence.map((e) => (
            <blockquote key={`${e.doc_id}${e.section}`} className="rounded-lg border border-line bg-canvas px-3 py-2">
              <div className="mb-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-muted">
                <span className="font-semibold text-ink">{e.doc_label}</span>
                <span>{e.section_label}</span>
                <span>· effective {e.effective_date}</span>
                <Badge tone={e.status === "current" ? "ok" : "bad"}>{e.status === "current" ? "Current" : "Superseded"}</Badge>
              </div>
              <p>{e.text}</p>
            </blockquote>
          ))}
        </div>
      ) : (
        sentence.label !== "Not a claim" && <p className="text-ink-muted">No current procedure passage covers this sentence.</p>
      )}
      {sentence.ignored_conflicting.length > 0 && (
        <p className="text-xs text-ink-muted">
          Left out because a newer document disagrees: {sentence.ignored_conflicting.join(", ")}.
        </p>
      )}
    </div>
  );
}

/** Plain-English explanation of every flag, most serious first. */
export function FlagList({ flags }: { flags: Flag[] }) {
  const order = { critical: 0, warning: 1, info: 2 };
  const sorted = [...flags].sort((a, b) => order[a.severity] - order[b.severity]);
  if (sorted.length === 0) return <p className="text-sm text-ok">All checks passed.</p>;
  return (
    <ul className="space-y-2">
      {sorted.map((f, i) => (
        <li key={i} className="flex gap-2 text-sm">
          <span className="shrink-0">
            <Badge tone={SEVERITY[f.severity].tone}>{SEVERITY[f.severity].text}</Badge>
          </span>
          <span>
            {f.message} <span className="text-xs text-ink-muted">({CHECK_NAMES[f.check]} check)</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Step 4C: was each part of the question answered? */
export function PartsList({ intent }: { intent: Checks["intent"] }) {
  return (
    <ol className="space-y-1.5 text-sm">
      {intent.map((p, i) => (
        <li key={i} className="flex flex-wrap items-center gap-2">
          <Badge tone={PART_STATUS[p.status].tone}>{PART_STATUS[p.status].text}</Badge>
          <span>
            {i + 1}. {p.part}
          </span>
        </li>
      ))}
    </ol>
  );
}

/** Step 4A: the four plain rules, pass or fail. */
export function RuleSummary({ rule }: { rule: Checks["rule"] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {(Object.keys(RULE_NAMES) as (keyof Checks["rule"])[]).map((k) => (
        <Badge key={k} tone={rule[k].passed ? "ok" : "bad"}>
          {rule[k].passed ? "Pass" : "Fail"}: {RULE_NAMES[k]}
        </Badge>
      ))}
    </div>
  );
}
