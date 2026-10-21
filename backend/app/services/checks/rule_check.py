"""Check A - rules and timeframes. Plain Python, NO LLM.

  citation_exists : the answer cites at least one real document section
  source_current  : every cited document is "current", not "superseded"
  figures_match   : every amount / percentage / number / date in a cited sentence
                    appears in the cited passage(s)
  quotes_match    : text in quotation marks appears word for word in the cited document

A citation covers its own sentence and any uncited sentences just before it.
"""
import re

from app.schemas.workflow import Flag
from app.services.knowledge_base import get_kb
from app.services.text import extract_figures, split_sentences
from app.services.verdict import make_flag

QUOTE_RE = re.compile(r"\"([^\"]{3,})\"|“([^”]{3,})”")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def run_rule_check(answer: str, ignore_figures: set[str] | None = None) -> dict:
    kb = get_kb()
    ignore = ignore_figures or set()
    sentences = split_sentences(answer)
    flags: list[Flag] = []

    # Which citations cover each sentence (its own, or the next one after it)
    effective, pending = [None] * len(sentences), []
    for s in reversed(sentences):
        if s.citations:
            pending = s.citations
        effective[s.index] = s.citations or pending

    # Resolve citations to documents and passages
    sentence_rows, cited_docs, unresolved = [], {}, []
    for s in sentences:
        cites, passages = [], []
        for c in effective[s.index]:
            doc = kb.doc_by_label(c.doc_label)
            found = [kb.passage(doc.id, sec) for sec in c.sections] if doc else []
            ok_sections = [sec for sec, p in zip(c.sections, found) if p]
            passages += [p for p in found if p]
            if doc is None or len(ok_sections) < len(c.sections):
                unresolved.append(f"{c.doc_label}, " + ", ".join(f"§{x}" for x in c.sections))
            if doc:
                cited_docs[doc.id] = doc
            cites.append({
                "label": c.doc_label, "sections": c.sections, "doc_id": doc.id if doc else None,
                "status": doc.status if doc else "unknown", "own": bool(s.citations),
            })
        sentence_rows.append({"index": s.index, "text": s.text, "raw": s.raw, "citations": cites,
                              "passages": [p.text for p in passages]})

    # citation_exists
    citation_exists = bool(cited_docs)
    if not citation_exists:
        flags.append(make_flag("A", "no_citation", "The answer does not cite any approved procedure."))
    for u in sorted(set(unresolved)):
        flags.append(make_flag("A", "citation_not_found", f"The cited source “{u}” does not exist in the knowledge base."))

    # source_current
    outdated = [d for d in cited_docs.values() if d.status != "current"]
    for d in outdated:
        newer = kb.doc(d.superseded_by) if d.superseded_by else None
        msg = f"The answer cites {d.label}, which is out of date"
        msg += f" and has been replaced by {newer.label}." if newer else "."
        flags.append(make_flag("A", "outdated_source", msg, doc_ids=[d.id]))

    # figures_match
    figure_problems = []
    for row in sentence_rows:
        if not row["passages"]:
            continue
        in_passages = {v for t in row["passages"] for _, v in extract_figures(t)}
        missing = [v for _, v in extract_figures(row["text"]) if v not in ignore and v not in in_passages]
        if missing:
            figure_problems.append(row["index"])
            shown = ", ".join(m.upper() if m.startswith("s$") else m for m in missing)
            flags.append(make_flag(
                "A", "figure_mismatch",
                f"{shown} in “{row['text']}” does not appear in the cited section.", row["index"],
                [c["doc_id"] for c in row["citations"] if c["doc_id"]],
            ))

    # quotes_match
    quote_problems = []
    for row in sentence_rows:
        for m in QUOTE_RE.finditer(row["raw"]):
            quote = m.group(1) or m.group(2)
            docs = {c["doc_id"] for c in row["citations"] if c["doc_id"]}
            texts = [p.text for d in docs for p in kb.doc(d).passages]
            if not any(_norm(quote) in _norm(t) for t in texts):
                quote_problems.append(quote)
                flags.append(make_flag(
                    "A", "quote_mismatch",
                    f"The quoted text “{quote}” does not appear word for word in the cited document.", row["index"],
                ))

    return {
        "rules": {
            "citation_exists": {"passed": citation_exists and not unresolved, "detail": sorted(set(unresolved))},
            "source_current": {"passed": not outdated, "detail": [d.label for d in outdated]},
            "figures_match": {"passed": not figure_problems, "detail": figure_problems},
            "quotes_match": {"passed": not quote_problems, "detail": quote_problems},
        },
        "sentences": [{k: v for k, v in r.items() if k != "passages"} for r in sentence_rows],
        "cited_doc_ids": list(cited_docs),
        "flags": [f.model_dump() for f in flags],
    }
