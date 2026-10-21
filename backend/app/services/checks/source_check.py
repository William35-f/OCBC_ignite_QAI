"""Check B - source check.

label_claims() is the sentence-level claim checker. It is also used in
Step 2 to check the assumptions inside a question.

For each claim:
  1. retrieve the top 3 passages from CURRENT documents only
  2. if a known conflict pair shows up, keep only the newer document's passage
  3. no passage above the similarity threshold -> "Unable to verify" (no LLM call)
Then ONE batched LLM call labels all remaining claims.
"""
from app.core.llm import call_json
from app.core.runtime import get_runtime
from app.schemas.workflow import ClaimLabels, ClaimResult, Evidence
from app.services.knowledge_base import KnowledgeBase, get_kb
from app.services.vector_store import Hit


def to_evidence(kb: KnowledgeBase, hit: Hit) -> Evidence:
    p, d = hit.passage, kb.doc(hit.passage.doc_id)
    return Evidence(
        doc_id=d.id, doc_label=d.label, version=d.version, status=d.status, section=p.section,
        section_label=p.section_label, effective_date=d.effective_date, text=p.text, score=hit.score,
    )


def drop_older_conflicting(kb: KnowledgeBase, hits: list[Hit], query: str) -> tuple[list[Hit], list[str]]:
    """When current documents disagree (a known conflict), trust the newer one.
    Passages of the older document that state the conflicting value are removed,
    and the newer document's best passage is added."""
    ignored: list[str] = []
    for c in kb.conflicts:
        stale = [h for h in hits if h.passage.doc_id == c.doc_b and c.value_b.lower() in h.passage.text.lower()]
        if stale:
            hits = [h for h in hits if h not in stale]
            ignored.append(f"{kb.doc(c.doc_b).label} {stale[0].passage.section_label}")
            if not any(h.passage.doc_id == c.doc_a for h in hits):
                hits += kb.search(query, 1, [c.doc_a])
    return sorted(hits, key=lambda h: -h.score), ignored


async def label_claims(
    claims: list[str],
    question: str,
    details: dict,
    ignore_figures: list[str] | None = None,
    threshold: float | None = None,
) -> list[ClaimResult]:
    kb = get_kb()
    threshold = get_runtime().similarity_threshold if threshold is None else threshold
    results: list[ClaimResult | None] = [None] * len(claims)
    to_label: list[tuple[int, list[Evidence], list[str]]] = []

    for i, claim in enumerate(claims):
        hits, ignored = drop_older_conflicting(kb, kb.search_current(claim, k=3), claim)
        passing = [h for h in hits if h.score >= threshold]
        if not passing:
            results[i] = ClaimResult(
                index=i, text=claim, label="Unable to verify",
                reason="No current procedure passage is close enough to this sentence to check it.",
                ignored_conflicting=ignored,
            )
        else:
            to_label.append((i, [to_evidence(kb, h) for h in passing], ignored))

    if to_label:
        payload = {
            "question": question,
            "details": details,
            "claims": [
                {
                    "id": i,
                    "text": claims[i],
                    "evidence": [
                        {"id": n, "doc_label": e.doc_label, "section_label": e.section_label,
                         "effective_date": e.effective_date, "text": e.text}
                        for n, e in enumerate(ev)
                    ],
                }
                for i, ev, _ in to_label
            ],
            # figures the employee typed themselves (e.g. "S$8,000") are not claims from a source
            "ignore_figures": ignore_figures or [],
        }
        labels = {lab.id: lab for lab in (await call_json("label_claims", payload, ClaimLabels)).labels}
        for i, ev, ignored in to_label:
            lab = labels.get(i)
            if lab is None:
                results[i] = ClaimResult(index=i, text=claims[i], label="Unsupported",
                                         reason="The checker returned no label for this sentence.", evidence=ev)
                continue
            chosen = [ev[n] for n in lab.evidence_ids if 0 <= n < len(ev)] or ev
            results[i] = ClaimResult(
                index=i, text=claims[i], label=lab.label, reason=lab.reason,
                correction=lab.correction if lab.label == "Contradicted" else None,
                evidence=chosen, ignored_conflicting=ignored,
            )
    return [r for r in results if r is not None]
