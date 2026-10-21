// Trust Challenge: can people spot wrong answers? Round A shows the text only,
// Round B the same answers with Q AI's evidence view. Order is shuffled each round.
import { useEffect, useState } from "react";
import { api, type RoundScore, type TrustItem } from "../api";
import { EvidencePanel, FlagList, HighlightedAnswer } from "../components/Evidence";
import { Badge, ErrorNote, Spinner } from "../components/ui";
import VerdictBanner from "../components/VerdictBanner";

type Phase = "intro" | "A" | "B" | "done";

function shuffle<T>(list: T[]): T[] {
  const a = [...list];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function newSessionId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `s-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
}

interface Score {
  score: { A: RoundScore; B: RoundScore };
  truth: Record<string, { trustworthy: boolean; why: string; question: string }>;
  choices: { round: string; item_id: string; choice: string; correct: boolean }[];
}

export default function TrustChallenge() {
  const [items, setItems] = useState<TrustItem[] | null>(null);
  const [phase, setPhase] = useState<Phase>("intro");
  const [order, setOrder] = useState<TrustItem[]>([]);
  const [index, setIndex] = useState(0);
  const [session, setSession] = useState("");
  const [score, setScore] = useState<Score | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<TrustItem[]>("/api/trust/items").then(setItems).catch((e) => setError(e.message));
  }, []);

  const startRound = (round: "A" | "B") => {
    setOrder(shuffle(items ?? []));
    setIndex(0);
    setSelected(null);
    setPhase(round);
  };

  const start = () => {
    setSession(newSessionId());
    setScore(null);
    startRound("A");
  };

  const choose = async (choice: "trust" | "dont_trust") => {
    const item = order[index];
    try {
      await api.post("/api/trust/answers", { session_id: session, round: phase, item_id: item.id, choice });
    } catch (e) {
      setError((e as Error).message);
      return;
    }
    if (index + 1 < order.length) {
      setIndex(index + 1);
      setSelected(null);
    } else if (phase === "A") {
      startRound("B");
    } else {
      setScore(await api.get<Score>(`/api/trust/score/${session}`));
      setPhase("done");
    }
  };

  if (!items) return error ? <ErrorNote message={error} /> : <Spinner />;
  const item = order[index];

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <h1 className="page-title">Trust Challenge</h1>
        <p className="muted">A short study: can people tell which AI answers to trust, with and without Q AI's evidence?</p>
      </div>
      {error && <ErrorNote message={error} />}

      {phase === "intro" && (
        <section className="card space-y-3">
          <p>You will see {items.length} answers to branch staff questions. Some are subtly wrong.</p>
          <ol className="list-decimal space-y-1 pl-5 text-sm">
            <li>
              <strong>Round A:</strong> the answer text only. Choose “Trust” or “Don't trust”.
            </li>
            <li>
              <strong>Round B:</strong> the same answers, in a new order, with Q AI's full evidence view.
            </li>
          </ol>
          <p className="text-sm text-ink-muted">Your choices are logged anonymously. It takes about 5 minutes.</p>
          <button className="btn-primary" onClick={start}>
            Start Round A
          </button>
        </section>
      )}

      {(phase === "A" || phase === "B") && item && (
        <section className="card space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Badge tone="brand">Round {phase}: {phase === "A" ? "text only" : "with evidence"}</Badge>
            <span className="text-sm text-ink-muted">
              {index + 1} of {order.length}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted-tint" aria-hidden="true">
            <div className="h-full bg-brand" style={{ width: `${((index + 1) / order.length) * 100}%` }} />
          </div>
          <p className="text-sm text-ink-muted">Question</p>
          <p className="text-lg font-semibold">{item.question}</p>
          <p className="text-sm text-ink-muted">OCBC AI's answer</p>
          {phase === "A" ? (
            <p className="rounded-xl border border-line bg-canvas px-4 py-3 text-[15px] leading-relaxed">{item.answer}</p>
          ) : (
            <div className="space-y-3">
              <VerdictBanner verdict={item.checks.verdict} inReview={false} />
              <HighlightedAnswer checks={item.checks} selected={selected} onSelect={setSelected} />
              <div className="rounded-xl border border-line p-4">
                <EvidencePanel sentence={item.checks.sentences.find((s) => s.index === selected)} />
              </div>
              <div className="rounded-xl border border-line p-4">
                <p className="mb-2 text-sm font-bold">Why this verdict</p>
                <FlagList flags={item.checks.flags} />
              </div>
            </div>
          )}
          <div className="flex flex-wrap gap-2 border-t border-line pt-4">
            <button className="btn-primary" onClick={() => choose("trust")}>
              Trust
            </button>
            <button className="btn-secondary" onClick={() => choose("dont_trust")}>
              Don't trust
            </button>
          </div>
        </section>
      )}

      {phase === "done" && score && (
        <section className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {(["A", "B"] as const).map((r) => (
              <div key={r} className="card">
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
                  Round {r}: {r === "A" ? "text only" : "with evidence"}
                </p>
                <p className="mt-1 text-3xl font-bold">
                  {score.score[r].correct} / {score.score[r].answers}
                </p>
                <p className="text-sm text-ink-muted">correct calls</p>
              </div>
            ))}
          </div>
          <div className="card space-y-2">
            <h2 className="font-bold">The answers</h2>
            <ul className="space-y-2 text-sm">
              {Object.entries(score.truth).map(([id, t]) => (
                <li key={id} className="flex gap-2">
                  <span className="shrink-0">
                    <Badge tone={t.trustworthy ? "ok" : "bad"}>{t.trustworthy ? "Trustworthy" : "Wrong"}</Badge>
                  </span>
                  <span>
                    {t.question} <span className="text-ink-muted">– {t.why}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <button className="btn-secondary" onClick={() => setPhase("intro")}>
            Start again (new participant)
          </button>
        </section>
      )}
    </div>
  );
}
