"""Step 3 - OCBC AI (simulated): a basic RAG assistant.

Deliberately imperfect: its retriever searches EVERY document whose retriever
switch is on, superseded ones included, and it never looks at document status.
"""
from sqlalchemy.orm import Session

from app.core.llm import call_text
from app.services.knowledge_base import get_kb, ocbc_enabled_doc_ids

TOP_K = 5


async def generate_answer(
    db: Session,
    question: str,
    details: dict,
    search_query: str,
    parts: list[str],
    feedback: str = "",
    previous_answer: str = "",
    flagged: list[str] | None = None,
) -> tuple[str, list[dict]]:
    """Return (answer text with citations, the passages it was given).

    For a Step 5b retry, `feedback` holds Q AI's flags and the correct passages,
    and `flagged` the sentences Q AI could not support."""
    kb = get_kb()
    hits = kb.search(search_query or question, TOP_K, ocbc_enabled_doc_ids(db))
    passages = [
        {
            "doc_id": h.passage.doc_id,
            "label": kb.doc(h.passage.doc_id).label,
            "section": h.passage.section,
            "section_label": h.passage.section_label,
            "heading": h.passage.heading,
            "kind": h.passage.kind,
            "text": h.passage.text,
            "score": h.score,
        }
        for h in hits
    ]
    payload = {
        "question": question,
        "details": details,
        "parts": parts,
        "passages": passages,
        "feedback": f"Your previous answer:\n{previous_answer}\n\n{feedback}" if feedback else "",
        "previous_answer": previous_answer,
        "flagged_sentences": flagged or [],
    }
    return await call_text("ocbc_answer", payload), passages
