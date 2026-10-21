"""Step 4 - run checks A, B and C in parallel, then build the sentence view.

Q AI has read-only access to the knowledge base. It never edits the answer.
"""
import asyncio

from app.schemas.workflow import Flag
from app.services.checks.intent_check import run_intent_check
from app.services.checks.rule_check import run_rule_check
from app.services.checks.source_check import run_source_check
from app.services.text import extract_figures
from app.services.verdict import decide


def question_figures(parts: list[str]) -> list[str]:
    """Figures the employee typed in the question parts (e.g. "S$8,000").
    An answer repeating them is not quoting a source. Assumption clauses are
    not parts, so an assumed limit is still checked."""
    return sorted({v for p in parts for _, v in extract_figures(p)})


async def run_checks(answer: str, question: str, details: dict, parts: list[str], topic: str | None) -> dict:
    ignore = question_figures(parts)
    rule, source, intent = await asyncio.gather(
        asyncio.to_thread(run_rule_check, answer, set(ignore)),
        run_source_check(answer, question, details, topic, ignore),
        run_intent_check(parts, answer, question, details, topic),
    )
    flags = [Flag(**f) for f in rule["flags"] + source["flags"] + intent["flags"]]

    # One row per sentence for the evidence view: citation (A) + label and evidence (B) + flags
    claims = {c["index"]: c for c in source["claims"]}
    sentences = []
    for row in rule["sentences"]:
        claim = claims.get(row["index"])
        sentences.append({
            "index": row["index"],
            "text": row["text"],
            "raw": row["raw"],
            "citations": row["citations"],
            "label": claim["label"] if claim else "Not a claim",
            "reason": claim["reason"] if claim else "",
            "correction": claim["correction"] if claim else None,
            "evidence": claim["evidence"] if claim else [],
            "ignored_conflicting": claim["ignored_conflicting"] if claim else [],
            "flag_types": [f.type for f in flags if f.sentence_index == row["index"]],
        })

    return {
        "verdict": decide(flags),
        "flags": [f.model_dump() for f in flags],
        "sentences": sentences,
        "rule": rule["rules"],
        "source": {k: source[k] for k in ("exceptions", "cited_doc_ids", "skipped_sentences")},
        "intent": intent["parts"],
        "ignored_figures": ignore,
    }
