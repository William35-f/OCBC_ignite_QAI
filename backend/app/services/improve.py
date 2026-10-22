"""Step 8 - record and improve.

  dashboard()    numbers for the admin dashboard, from the logged runs
  suggestions()  fix suggestions from fixed TEMPLATES (not AI-generated):
                   superseded source cited -> "Retire <doc> from OCBC AI's retriever"
                   known conflict          -> "Resolve conflict between <doc A> and <doc B>"
                   Unable to verify        -> "Add coverage for <topic>"
  retire()       the "Apply fix" button: exclude a document from OCBC AI's retriever
  run_retest()   rerun the golden set + held-out questions through the full workflow.
                 A fix only counts as done once a retest passes.
"""
import json
from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Conflict, Document, EventLog, FixAction, GoldenItem, RetestRun, ReviewItem, Run
from app.services import workflow
from app.services.audit import log_event
from app.services.knowledge_base import get_kb
from app.services.text import extract_figures

PROBLEM = ("critical", "warning")


def _chat_runs(db: Session) -> list[Run]:
    return list(db.scalars(select(Run).where(Run.source == "chat", Run.status == "done").order_by(Run.id)))


def _problem_flags(checks: dict | None) -> list[dict]:
    return [f for f in (checks or {}).get("flags", []) if f["severity"] in PROBLEM]


def _label(doc_id: str) -> str:
    d = get_kb().doc(doc_id)
    return d.label if d else doc_id


# =============================================================================
# Dashboard
# =============================================================================
def dashboard(db: Session) -> dict:
    runs = _chat_runs(db)

    by_day: dict[str, Counter] = defaultdict(Counter)
    for r in runs:
        by_day[r.created_at.strftime("%Y-%m-%d")][r.final_verdict] += 1
    verdicts_over_time = [
        {"day": day, "Green": c["Green"], "Amber": c["Amber"], "Red": c["Red"]} for day, c in sorted(by_day.items())
    ]

    # Flags on OCBC AI's first answers: what goes wrong before Q AI steps in.
    # Errors are counted against the documents OCBC AI CITED (the cause), not the
    # current documents Q AI used as evidence (which caught the error).
    flag_counts: Counter = Counter()
    doc_errors: dict[str, Counter] = defaultdict(Counter)
    for r in runs:
        cited = ((r.original_checks or {}).get("source") or {}).get("cited_doc_ids") or ["(no document cited)"]
        for f in _problem_flags(r.original_checks):
            flag_counts[f["type"]] += 1
            for d in cited:
                doc_errors[d][f["type"]] += 1

    topics: dict[str, Counter] = defaultdict(Counter)
    for r in runs:
        topic = (r.prompt_check or {}).get("coverage_topic") or r.topic or "unknown"
        topics[topic]["total"] += 1
        if r.final_verdict != "Green":
            topics[topic]["failed"] += 1

    reviews = list(db.scalars(select(ReviewItem)))
    decisions = Counter(i.status for i in reviews if i.status != "pending")
    retried = [r for r in runs if r.retried]
    return {
        "totals": {
            "answers": len(runs),
            "green": sum(r.final_verdict == "Green" for r in runs),
            "amber": sum(r.final_verdict == "Amber" for r in runs),
            "red": sum(r.final_verdict == "Red" for r in runs),
            "retried": len(retried),
            "fixed_by_retry": sum(r.retry_verdict == "Green" for r in retried),
            "pending_reviews": sum(i.status == "pending" for i in reviews),
            "used": sum(r.employee_action == "used" for r in runs),
            "reported": sum(r.employee_action == "reported" for r in runs),
            "golden": db.query(GoldenItem).count(),
        },
        "verdicts_over_time": verdicts_over_time,
        "flag_counts": [{"type": t, "count": n} for t, n in flag_counts.most_common()],
        "topic_failures": sorted(
            ({"topic": t, "failed": c["failed"], "total": c["total"]} for t, c in topics.items()),
            key=lambda x: (-x["failed"], x["topic"]),
        ),
        "doc_errors": sorted(
            ({"doc_id": d, "doc_label": _label(d), "errors": dict(c), "total": sum(c.values())}
             for d, c in doc_errors.items()),
            key=lambda x: -x["total"],
        ),
        "reviewer_decisions": {k: decisions.get(k, 0) for k in ("approved", "corrected", "rejected")},
    }


def activity(db: Session, limit: int = 40) -> list[dict]:
    """The latest audit-log events, newest first."""
    rows = db.execute(
        select(EventLog, Run.question).outerjoin(Run, Run.id == EventLog.run_id).order_by(EventLog.id.desc()).limit(limit)
    ).all()
    return [
        {"id": e.id, "at": e.created_at.isoformat(), "event": e.event, "actor": e.actor, "run_id": e.run_id,
         "question": q, "data": e.data}
        for e, q in rows
    ]


# =============================================================================
# Fix suggestions (templates)
# =============================================================================
def _fix_status(db: Session, kind: str, target: str) -> str:
    fix = db.scalar(select(FixAction).where(FixAction.kind == kind, FixAction.target == target)
                    .order_by(FixAction.id.desc()))
    if fix is None:
        return "open"
    return "done" if fix.status == "verified" else "applied"


def suggestions(db: Session) -> list[dict]:
    runs = _chat_runs(db)
    out = []

    # 1. Superseded source cited -> retire it
    cited_outdated: Counter = Counter()
    for r in runs:
        for f in _problem_flags(r.original_checks) + _problem_flags(r.retry_checks):
            if f["type"] == "outdated_source":
                for d in f.get("doc_ids") or []:
                    cited_outdated[d] += 1
    for doc_id, n in cited_outdated.most_common():
        row = db.get(Document, doc_id)
        status = _fix_status(db, "retire_document", doc_id)
        if row is not None and row.retriever_enabled and status != "open":
            status = "open"  # switched back on by hand: the problem is back
        evidence = (f"{_label(doc_id)} is still being retrieved by OCBC AI: it was cited in {n} answer(s) "
                    f"although a newer version has replaced it." if row is None or row.retriever_enabled
                    else f"{_label(doc_id)} was cited in {n} answer(s). It is now excluded from OCBC AI's retriever.")
        out.append({
            "id": f"retire:{doc_id}", "kind": "retire_document", "target": doc_id,
            "title": f"Retire {_label(doc_id)} from OCBC AI's retriever",
            "evidence": evidence, "count": n, "status": status,
            "can_apply": bool(row and row.retriever_enabled),
        })

    # 2. Known conflicts -> resolve them (the document owners have to do this)
    conflict_hits: Counter = Counter()
    for r in runs:
        for f in (r.original_checks or {}).get("flags", []) + (r.retry_checks or {}).get("flags", []):
            if f["type"] in ("conflict_older_source", "conflict_note"):
                conflict_hits[tuple(sorted(f.get("doc_ids") or []))] += 1
    for c in db.scalars(select(Conflict)):
        n = conflict_hits[tuple(sorted([c.doc_a, c.doc_b]))]
        out.append({
            "id": f"conflict:{c.id}", "kind": "resolve_conflict", "target": f"{c.doc_a}|{c.doc_b}",
            "title": f"Resolve conflict between {_label(c.doc_a)} and {_label(c.doc_b)}",
            "evidence": (f"They disagree on {c.field.replace('_', ' ')}: {c.value_a} vs {c.value_b}. "
                         f"Seen in {n} answer(s). Ask the owners to update or retire {_label(c.doc_b)}."),
            "count": n, "status": "open", "can_apply": False,
        })

    # 3. "Unable to verify" -> add coverage for that topic
    gaps: Counter = Counter()
    for r in runs:
        checks = r.retry_checks or r.original_checks
        if any(f["type"] == "unable_to_verify" for f in _problem_flags(checks)):
            gaps[(r.prompt_check or {}).get("coverage_topic") or r.topic or "unknown"] += 1
    for topic, n in gaps.most_common():
        out.append({
            "id": f"coverage:{topic}", "kind": "add_coverage", "target": topic,
            "title": f"Add coverage for {topic.replace('_', ' ')}",
            "evidence": f"{n} answer(s) on this had no approved source to check against.",
            "count": n, "status": "open", "can_apply": False,
        })
    return out


def retire(db: Session, doc_id: str, actor: str = "Priya Nair") -> FixAction:
    """Apply fix: exclude a document from OCBC AI's retriever (Q AI can still read it)."""
    row = db.get(Document, doc_id)
    if row is None:
        raise ValueError("Unknown document")
    row.retriever_enabled = False
    row.retired_at = datetime.now()
    fix = FixAction(kind="retire_document", target=doc_id, status="applied")
    db.add(fix)
    log_event(db, "fix_applied", actor=actor, kind="retire_document", doc_id=doc_id)
    db.commit()
    return fix


# =============================================================================
# Retest
# =============================================================================
def load_heldout() -> list[dict]:
    path = settings.eval_dir / "heldout.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _figures(text: str) -> set[str]:
    return {v for _, v in extract_figures(text or "")}


async def _run_case(db: Session, question: str, details: dict) -> Run:
    run = await workflow.start_run(db, question, details, user_name="Retest", source="retest")
    if run.status == "running":
        await workflow.process_run(run.id)
    db.expire_all()
    return db.get(Run, run.id)


async def run_retest(db: Session, actor: str = "Priya Nair") -> RetestRun:
    results = []
    for g in db.scalars(select(GoldenItem).order_by(GoldenItem.id)):
        run = await _run_case(db, g.question, g.details or {})
        missing = sorted(_figures(g.correct_answer) - _figures(run.final_answer))
        passed = run.status == "done" and run.final_verdict == "Green" and not missing
        reason = ("Green and matches the golden answer" if passed else
                  "Still asks for details" if run.status == "needs_details" else
                  f"Verdict {run.final_verdict}, expected Green" if run.final_verdict != "Green" else
                  f"Missing figures from the golden answer: {', '.join(missing)}")
        results.append({"kind": "golden", "question": g.question, "details": g.details, "expected": "Green",
                        "got": run.final_verdict, "passed": passed, "reason": reason,
                        "answer": run.final_answer, "run_id": run.id})

    for case in load_heldout():
        run = await _run_case(db, case["question"], case.get("details") or {})
        passed = run.status == "done" and run.final_verdict == case["expected_verdict"]
        results.append({"kind": "held-out", "question": case["question"], "details": case.get("details") or {},
                        "expected": case["expected_verdict"], "got": run.final_verdict, "passed": passed,
                        "reason": case.get("note", ""), "answer": run.final_answer, "run_id": run.id})

    retest = RetestRun(passed=bool(results) and all(r["passed"] for r in results), results=results)
    db.add(retest)
    if retest.passed:  # applied fixes now count as done
        for fix in db.scalars(select(FixAction).where(FixAction.status == "applied")):
            fix.status, fix.verified_at = "verified", datetime.now()
    log_event(db, "retest_run", actor=actor, passed=retest.passed,
              passed_count=sum(r["passed"] for r in results), total=len(results))
    db.commit()
    return retest


def retest_to_dict(r: RetestRun | None) -> dict | None:
    if r is None:
        return None
    return {"id": r.id, "created_at": r.created_at.isoformat(), "passed": r.passed, "results": r.results,
            "passed_count": sum(x["passed"] for x in r.results), "total": len(r.results)}
