"""Step 2 - prompt check (Q AI), before OCBC AI answers.

One LLM call returns: parts, topic, missing_details, assumptions, search_query.
Python then applies the guard-rails (only the matching document's required
details, at most N follow-ups) and runs each assumption through the claim
checker. A contradicted assumption becomes a correction note.
"""
import re

from app.core.llm import call_json
from app.core.runtime import get_runtime
from app.schemas.workflow import PromptCheckResult
from app.services.checks.source_check import label_claims
from app.services.knowledge_base import get_kb
from app.services.text import STOPWORDS, keywords, stem


# Follow-up questions are only asked when the knowledge base clearly covers the
# question. Asking "new or existing payee?" about crypto, which no procedure
# covers, would not help anyone.
STRONG_MATCH = 0.5


def _candidate_documents(question: str) -> list[dict]:
    """The current documents closest to the question, most relevant first."""
    kb, seen, docs = get_kb(), set(), []
    for hit in kb.search_current(question, k=6):
        d = kb.doc(hit.passage.doc_id)
        if d.id in seen:
            continue
        seen.add(d.id)
        docs.append({"id": d.id, "label": d.label, "topic": d.topic, "required_details": d.required_details,
                     "score": hit.score})
    return docs[:3]


def _topic_required_details(candidates: list[dict]) -> list[dict]:
    """Required details of the matching topic: those of every candidate document
    on the same topic as the best match (e.g. Branch FAQ ranks first, but
    Payments Procedure v2026 on the same topic needs payee_type)."""
    if not candidates:
        return []
    topic, seen, out = candidates[0]["topic"], set(), []
    for d in candidates:
        for rd in d["required_details"] if d["topic"] == topic else []:
            if rd["name"] not in seen:
                seen.add(rd["name"])
                out.append(rd)
    return out


async def run_prompt_check(question: str, details: dict) -> dict:
    rt = get_runtime()
    candidates = _candidate_documents(question)
    strong = bool(candidates) and candidates[0]["score"] >= STRONG_MATCH
    required = _topic_required_details(candidates) if strong else []
    result = await call_json(
        "prompt_check",
        {
            "question": question,
            "details": details,
            "candidate_documents": [{k: d[k] for k in ("label", "topic")} for d in candidates],
            "required_details": required,
            "max_followups": rt.max_followups,
        },
        PromptCheckResult,
    )

    # Guard-rails: only ask for the matching topic's required details, never twice, at most N
    allowed = {rd["name"] for rd in required}
    known = {**result.known_details, **details}
    missing = [f for f in result.missing_details if f.name in allowed and f.name not in known][: rt.max_followups]

    # Assumptions go through the Step 4B claim checker
    checks = await label_claims(result.assumptions, question, known) if result.assumptions else []
    notes = []
    for c in checks:
        if c.label == "Contradicted":
            ev = c.evidence[0] if c.evidence else None
            notes.append(c.correction or (f"Note: {ev.doc_label} {ev.section_label} says: “{ev.text}”" if ev else c.reason))

    return {
        "parts": result.parts,
        "topic": result.topic or (candidates[0]["topic"] if candidates else "general"),
        "missing_details": [f.model_dump() for f in missing],
        "assumptions": result.assumptions,
        "search_query": result.search_query.strip() or question,
        "known_details": result.known_details,
        "details_used": known,
        "assumption_checks": [c.model_dump() for c in checks],
        "correction_notes": notes,
        "matched_document": candidates[0]["label"] if candidates else None,
        "covered": strong,
        "coverage_topic": (result.topic or candidates[0]["topic"]) if strong else _uncovered_terms(question),
    }


def _uncovered_terms(question: str) -> str:
    """For a question no document covers well: the words in it that no
    document uses (e.g. "cryptocurrency crypto wallet"). Used by the
    "Add coverage for <topic>" fix suggestion."""
    kb = get_kb()
    known = set().union(*(keywords(f"{p.heading} {p.text}") for d in kb.docs.values() for p in d.passages))
    ordered = [stem(t) for t in re.findall(r"[a-z][a-z'-]*[a-z]", question.lower()) if t not in STOPWORDS]
    words = [w for w in dict.fromkeys(ordered) if w not in known]
    return " ".join(words[:4]) or "questions not covered by any procedure"
