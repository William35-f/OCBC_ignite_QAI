"""Check C - intent check: is every part of the question answered?

Uses the parts from Step 2 as a checklist. One LLM call returns
answered / partly / not_answered for each part. The LLM also gets, for
context, the current passages closest to each part and the conditions
that apply to the question.
"""
from app.core.llm import call_json
from app.core.runtime import get_runtime
from app.schemas.workflow import Flag, IntentResult
from app.services.checks.source_check import relevant_current_docs
from app.services.knowledge_base import get_kb
from app.services.verdict import make_flag


async def run_intent_check(parts: list[str], answer: str, question: str, details: dict, topic: str | None) -> dict:
    kb = get_kb()
    threshold = get_runtime().similarity_threshold
    detail_text = " ".join(f"{v} {k.split('_')[0]}" for k, v in details.items())

    references = {}
    for part in parts:
        hits = [h for h in kb.search_current(f"{part} {detail_text}".strip(), k=3) if h.score >= threshold]
        references[part] = [f"{kb.doc(h.passage.doc_id).label} {h.passage.section_label}: {h.passage.text}" for h in hits]

    conditions = [
        {"document": d.label, "text": c.text, "key_phrase": c.key_phrase}
        for d in relevant_current_docs(kb, topic, []) for c in d.conditions if c.applies(question, details)
    ]
    result = await call_json(
        "intent_check",
        {"question": question, "details": details, "parts": parts, "answer": answer,
         "reference_passages": references, "applicable_conditions": conditions},
        IntentResult,
    )

    # Keep the original part wording and order, whatever the model echoed back
    by_part = {p.part.strip().lower(): p for p in result.parts}
    rows: list[dict] = []
    flags: list[Flag] = []
    for n, part in enumerate(parts, start=1):
        item = by_part.get(part.strip().lower()) or (result.parts[n - 1] if n - 1 < len(result.parts) else None)
        status = item.status if item else "not_answered"
        reason = item.reason if item else "The checker returned no result for this part."
        rows.append({"part": part, "status": status, "reason": reason})
        if status == "partly":
            flags.append(make_flag("C", "part_partly_answered", f"Part {n} “{part}” is only partly answered. {reason}"))
        elif status == "not_answered":
            flags.append(make_flag("C", "part_not_answered", f"Part {n} “{part}” is not answered. {reason}"))
    return {"parts": rows, "flags": [f.model_dump() for f in flags]}
