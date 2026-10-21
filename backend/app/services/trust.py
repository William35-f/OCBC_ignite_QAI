"""Trust Challenge - a small user study.

Ten answers (five subtly wrong) are shown twice, in a shuffled order:
  Round A: answer text only               -> Trust / Don't trust
  Round B: the same answers with Q AI's full evidence view
Accuracy in A vs B shows whether the evidence view helps people judge answers.
"""
import json
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.eval import load_cases
from app.models import TrustResult
from app.services.checks.runner import run_checks


@lru_cache(maxsize=1)
def _items_spec() -> list[dict]:
    data = json.loads((settings.eval_dir / "trust_items.json").read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in load_cases()}
    return [{**cases[i["case_id"]], "trustworthy": i["trustworthy"], "why": i["why"]} for i in data["items"]]


_checks_cache: dict[str, dict] = {}


async def items() -> list[dict]:
    """The ten answers with Q AI's checks (computed once). The ground truth is NOT included."""
    out = []
    for c in _items_spec():
        if c["id"] not in _checks_cache:
            _checks_cache[c["id"]] = await run_checks(
                c["answer"], c["question"], c.get("details") or {}, c.get("parts") or [c["question"]], c.get("topic"))
        out.append({"id": c["id"], "question": c["question"], "answer": c["answer"], "checks": _checks_cache[c["id"]]})
    return out


def record(db: Session, session_id: str, round_: str, item_id: str, choice: str) -> TrustResult:
    truth = {c["id"]: c["trustworthy"] for c in _items_spec()}
    if round_ not in ("A", "B") or choice not in ("trust", "dont_trust") or item_id not in truth:
        raise ValueError("Invalid answer")
    # One answer per participant, round and item: a second click replaces the first
    existing = db.scalar(select(TrustResult).where(
        TrustResult.session_id == session_id, TrustResult.round == round_, TrustResult.item_id == item_id))
    row = existing or TrustResult(session_id=session_id, round=round_, item_id=item_id)
    row.choice = choice
    row.correct = (choice == "trust") == truth[item_id]
    db.add(row)
    db.commit()
    return row


def _accuracy(rows: list[TrustResult]) -> dict:
    out = {}
    for rnd in ("A", "B"):
        r = [x for x in rows if x.round == rnd]
        out[rnd] = {"answers": len(r), "correct": sum(x.correct for x in r),
                    "accuracy": round(sum(x.correct for x in r) / len(r), 3) if r else None}
    return out


def session_score(db: Session, session_id: str) -> dict:
    rows = list(db.scalars(select(TrustResult).where(TrustResult.session_id == session_id)))
    truth = {c["id"]: {"trustworthy": c["trustworthy"], "why": c["why"], "question": c["question"]} for c in _items_spec()}
    return {"score": _accuracy(rows), "truth": truth,
            "choices": [{"round": r.round, "item_id": r.item_id, "choice": r.choice, "correct": r.correct} for r in rows]}


def summary(db: Session) -> dict:
    """All participants, for the Admin dashboard."""
    rows = list(db.scalars(select(TrustResult)))
    sessions = {r.session_id for r in rows}
    complete = [s for s in sessions if sum(r.session_id == s for r in rows) >= 2 * len(_items_spec())]
    return {"participants": len(sessions), "completed": len(complete), **_accuracy(rows)}
