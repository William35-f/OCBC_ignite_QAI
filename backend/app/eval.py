"""Proof it works: evaluate Q AI on a labelled test set.

    python -m app.eval            (from backend/; or `npm run eval` from the project root)

1. data/eval/cases.jsonl - 40 pre-written answers (10 each: correct, missing
   exception, outdated source, no evidence). Q AI's checks run on each answer
   directly, bypassing OCBC AI. Reported:
     - missed errors : bad answers that came out Green
     - false flags   : correct answers that did not come out Green
     - accuracy per check (A, B, C): did the check flag the case exactly when
       the case expects that check to flag it?
2. Amber answers fixed by one retry: the demo questions and the held-out
   questions run through the FULL workflow (OCBC AI included).

Results are saved to data/eval/results.json and shown on the Admin dashboard.
"""
import asyncio
import json
from collections import defaultdict
from datetime import datetime

from app.core.config import settings
from app.core.db import SessionLocal, init_db
from app.services.checks.runner import run_checks
from app.services.demo import SCENARIOS
from app.services.improve import _run_case, load_heldout
from app.services.knowledge_base import get_kb, sync_to_db

# Which check raises which flag type
CHECK_OF = {
    "outdated_source": "A", "quote_mismatch": "A", "no_citation": "A", "citation_not_found": "A",
    "figure_mismatch": "A",
    "contradicted": "B", "missing_exception": "B", "partly_supported": "B", "unsupported": "B",
    "unable_to_verify": "B", "conflict_older_source": "B",
    "part_partly_answered": "C", "part_not_answered": "C",
}


def load_cases() -> list[dict]:
    path = settings.eval_dir / "cases.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def evaluate_case(case: dict) -> dict:
    parts = case.get("parts") or [case["question"]]
    checks = await run_checks(case["answer"], case["question"], case.get("details") or {}, parts, case.get("topic"))
    got_flags = sorted({f["type"] for f in checks["flags"] if f["severity"] in ("critical", "warning")})
    expected = case["expected_flags"]
    per_check = {}
    for check in "ABC":
        want = any(CHECK_OF.get(t) == check for t in expected)
        have = any(CHECK_OF.get(t) == check for t in got_flags)
        per_check[check] = want == have
    return {
        "id": case["id"], "type": case["type"], "question": case["question"],
        "expected_verdict": case["expected_verdict"], "got_verdict": checks["verdict"],
        "verdict_ok": checks["verdict"] == case["expected_verdict"],
        "expected_flags": expected, "got_flags": got_flags,
        "missing_flags": [t for t in expected if t not in got_flags],
        "per_check": per_check,
    }


async def retry_study() -> dict:
    """Run real questions through the full workflow and count Amber answers fixed by one retry."""
    questions = [(s["question"], {"payee_type": "New"} if s["id"] == "red" else {}) for s in SCENARIOS]
    questions += [(h["question"], h.get("details") or {}) for h in load_heldout()]
    rows = []
    with SessionLocal() as db:
        for q, details in questions:
            run = await _run_case(db, q, details)
            if run.original_verdict == "Amber":
                rows.append({"question": q, "retry_verdict": run.retry_verdict, "fixed": run.retry_verdict == "Green"})
            # eval runs are tagged so they never show up in the dashboard or review queue
            run.source = "eval"
            db.commit()
    fixed = sum(r["fixed"] for r in rows)
    return {"amber_first": len(rows), "fixed": fixed, "rate": round(fixed / len(rows), 3) if rows else None,
            "rows": rows}


async def run_eval(save: bool = True) -> dict:
    init_db()
    kb = get_kb()
    with SessionLocal() as db:
        sync_to_db(db, kb)

    rows = [await evaluate_case(c) for c in load_cases()]
    n = len(rows)
    bad = [r for r in rows if r["expected_verdict"] != "Green"]
    good = [r for r in rows if r["expected_verdict"] == "Green"]
    missed = [r["id"] for r in bad if r["got_verdict"] == "Green"]
    false_flags = [r["id"] for r in good if r["got_verdict"] != "Green"]
    expected_total = sum(len(r["expected_flags"]) for r in rows)
    found_total = sum(len(r["expected_flags"]) - len(r["missing_flags"]) for r in rows)

    by_type: dict[str, dict] = defaultdict(lambda: {"cases": 0, "verdict_ok": 0})
    for r in rows:
        by_type[r["type"]]["cases"] += 1
        by_type[r["type"]]["verdict_ok"] += r["verdict_ok"]

    results = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "provider": __import__("app.core.runtime", fromlist=["get_runtime"]).get_runtime().llm_provider,
        "cases": n,
        "verdict_accuracy": round(sum(r["verdict_ok"] for r in rows) / n, 3),
        "missed_errors": {"count": len(missed), "of": len(bad), "ids": missed},
        "false_flags": {"count": len(false_flags), "of": len(good), "ids": false_flags},
        "per_check_accuracy": {c: round(sum(r["per_check"][c] for r in rows) / n, 3) for c in "ABC"},
        "flag_recall": round(found_total / expected_total, 3) if expected_total else None,
        "by_type": dict(by_type),
        "retry": await retry_study(),
        "rows": rows,
    }
    if save:
        path = settings.eval_dir / "results.json"
        path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return results


def _print(results: dict) -> None:
    print(f"\nQ AI evaluation - {results['cases']} cases, provider: {results['provider']}")
    print(f"  Verdict accuracy : {results['verdict_accuracy']:.0%}")
    m, f = results["missed_errors"], results["false_flags"]
    print(f"  Missed errors    : {m['count']} of {m['of']} bad answers came out Green {m['ids'] or ''}")
    print(f"  False flags      : {f['count']} of {f['of']} correct answers were flagged {f['ids'] or ''}")
    pc = results["per_check_accuracy"]
    print(f"  Accuracy per check: A {pc['A']:.0%} · B {pc['B']:.0%} · C {pc['C']:.0%}")
    print(f"  Expected flags found: {results['flag_recall']:.0%}")
    rt = results["retry"]
    print(f"  Amber fixed by one retry: {rt['fixed']} of {rt['amber_first']}")
    wrong = [r for r in results["rows"] if not r["verdict_ok"] or r["missing_flags"] or not all(r["per_check"].values())]
    if wrong:
        print("\n  Cases that did not fully match:")
        for r in wrong:
            checks = "".join(c for c, ok in r["per_check"].items() if not ok)
            print(f"   {r['id']}: expected {r['expected_verdict']}, got {r['got_verdict']}"
                  f"{' | checks off: ' + checks if checks else ''}"
                  f"{' | missing: ' + ', '.join(r['missing_flags']) if r['missing_flags'] else ''}")
    print(f"\n  Saved to {settings.eval_dir / 'results.json'}")


def main() -> None:
    _print(asyncio.run(run_eval()))


if __name__ == "__main__":
    main()
