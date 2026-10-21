"""Check B - source check.

run_source_check() does three things:
  1. sentence level: label_claims() on every sentence of the answer
  2. counter-evidence (a): missing exceptions - one LLM call over the
     "Conditions and exceptions" of the relevant current documents
  3. counter-evidence (b): known conflicts - a lookup in the conflicts table
     computed at load time (nothing is computed per answer)

label_claims() is also used in Step 2 to check the assumptions inside a question.

For each claim:
  1. retrieve the top 3 passages from CURRENT documents only
  2. if a known conflict pair shows up, keep only the newer document's passage
  3. no passage above the similarity threshold -> "Unable to verify" (no LLM call)
Then ONE batched LLM call labels all remaining claims.
"""
import asyncio

from app.core.llm import call_json
from app.core.runtime import get_runtime
from app.schemas.workflow import ClaimLabels, ClaimResult, Evidence, ExceptionChecks, Flag
from app.services.ingest import KBDocument
from app.services.knowledge_base import KnowledgeBase, get_kb
from app.services.text import NO_SOURCE_RE, keywords, split_sentences
from app.services.vector_store import Hit
from app.services.verdict import make_flag


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
        if NO_SOURCE_RE.search(claim):  # "No approved source was found ..." cannot be checked against a source
            results[i] = ClaimResult(index=i, text=claim, label="Unable to verify",
                                     reason="The answer itself says no approved source covers this.")
            continue
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


# =============================================================================
# The full Check B for one answer
# =============================================================================
LABEL_FLAG = {
    "Contradicted": "contradicted",
    "Partly supported": "partly_supported",
    "Unsupported": "unsupported",
    "Unable to verify": "unable_to_verify",
}


def is_claim(sentence: str) -> bool:
    """"Yes." / "No." on their own are not factual claims to check."""
    return bool(keywords(sentence) - {"yes", "no"})


def relevant_current_docs(kb: KnowledgeBase, topic: str | None, cited_doc_ids: list[str]) -> list[KBDocument]:
    """Current documents whose conditions might apply: the question's topic,
    the cited documents, and the current replacements of cited superseded ones."""
    ids: list[str] = [d.id for d in kb.docs.values() if d.topic == topic and d.status == "current"]
    for doc_id in cited_doc_ids:
        d = kb.doc(doc_id)
        while d and d.status != "current" and d.superseded_by:
            d = kb.doc(d.superseded_by)
        if d and d.status == "current":
            ids.append(d.id)
    return [kb.doc(i) for i in dict.fromkeys(ids)]


async def check_missing_exceptions(answer: str, question: str, details: dict, docs: list[KBDocument]) -> list[dict]:
    """One LLM call: which conditions apply to this question, and does the answer mention them?"""
    conditions = [
        {"id": f"{d.id}:{c.id}", "document": d.label, "section": f"§{c.section_ref}" if c.section_ref else c.id,
         "text": c.text, "key_phrase": c.key_phrase, "applies_when": c.when,
         # rule-based hint used by the mock provider
         "applies_by_rule": c.applies(question, details)}
        for d in docs for c in d.conditions
    ]
    if not conditions:
        return []
    result = await call_json(
        "missing_exceptions",
        {"question": question, "details": details, "answer": answer, "conditions": conditions},
        ExceptionChecks,
    )
    by_id = {c["id"]: c for c in conditions}
    return [
        {**by_id[item.id], "applies": item.applies, "mentioned": item.mentioned, "reason": item.reason}
        for item in result.conditions if item.id in by_id
    ]


def conflict_flags(kb: KnowledgeBase, cited_doc_ids: list[str]) -> list[Flag]:
    """Look up cited documents in the conflicts table (computed once at load time)."""
    flags = []
    for doc_id in cited_doc_ids:
        for c in kb.conflicts_for(doc_id):
            newer, older = kb.doc(c.doc_a), kb.doc(c.doc_b)
            field = c.field.replace("_", " ")
            if doc_id == c.doc_b:
                msg = (f"{older.label} conflicts with the newer {newer.label} on {field} "
                       f"({c.value_b} vs {c.value_a}). The newer document should be followed.")
                flags.append(make_flag("B", "conflict_older_source", msg, doc_ids=[c.doc_b, c.doc_a]))
            else:
                msg = (f"Note: {older.label} still says {c.value_b} for {field}. This answer follows the newer "
                       f"{newer.label} ({c.value_a}).")
                flags.append(make_flag("B", "conflict_note", msg, doc_ids=[c.doc_a, c.doc_b]))
    return flags


async def run_source_check(
    answer: str, question: str, details: dict, topic: str | None, ignore_figures: list[str] | None = None
) -> dict:
    kb = get_kb()
    sentences = split_sentences(answer)
    claim_rows = [s for s in sentences if is_claim(s.text)]

    # Cited documents (parsed here so Check B does not depend on Check A)
    cited = []
    for s in sentences:
        for c in s.citations:
            d = kb.doc_by_label(c.doc_label)
            if d and d.id not in cited:
                cited.append(d.id)

    labelled, exceptions = await asyncio.gather(
        label_claims([s.text for s in claim_rows], question, details, ignore_figures=ignore_figures),
        check_missing_exceptions(answer, question, details, relevant_current_docs(kb, topic, cited)),
    )

    flags: list[Flag] = []
    claims = []
    for row, result in zip(claim_rows, labelled):
        result.index = row.index
        claims.append(result.model_dump())
        if result.label in LABEL_FLAG:
            short = row.text if len(row.text) < 90 else row.text[:87] + "..."
            msg = {
                "Contradicted": f"“{short}” is contradicted by "
                                + (f"{result.evidence[0].doc_label} {result.evidence[0].section_label}." if result.evidence else "a current procedure."),
                "Partly supported": f"“{short}” is only partly supported by current procedures.",
                "Unsupported": f"“{short}” is not stated in any current procedure.",
                "Unable to verify": f"“{short}” could not be checked: no approved source covers it.",
            }[result.label]
            if result.correction:
                msg += f" {result.correction}"
            flags.append(make_flag("B", LABEL_FLAG[result.label], msg, row.index,
                                   [e.doc_id for e in result.evidence]))

    for ex in exceptions:
        if ex["applies"] and not ex["mentioned"]:
            flags.append(make_flag(
                "B", "missing_exception",
                f"The answer leaves out a required condition from {ex['document']} {ex['section']}: {ex['text']}",
                doc_ids=[ex["id"].split(":")[0]],
            ))

    flags += conflict_flags(kb, cited)
    return {
        "claims": claims,
        "skipped_sentences": [s.index for s in sentences if not is_claim(s.text)],
        "exceptions": exceptions,
        "cited_doc_ids": cited,
        "flags": [f.model_dump() for f in flags],
    }
