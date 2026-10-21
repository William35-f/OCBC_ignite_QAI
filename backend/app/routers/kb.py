"""Knowledge base page: documents, retriever switch, known conflicts, search."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Conflict, Document, EventLog
from app.schemas.kb import ConflictOut, DocumentOut, PassageOut, ConditionOut, RetrieverToggle, SearchHitOut
from app.services.knowledge_base import get_kb, ocbc_enabled_doc_ids

router = APIRouter(prefix="/api/kb", tags=["knowledge base"])


def _doc_out(row: Document, with_content: bool) -> DocumentOut:
    kb_doc = get_kb().doc(row.id)
    out = DocumentOut(
        id=row.id,
        label=kb_doc.label if kb_doc else row.title,
        title=row.title,
        version=row.version,
        topic=row.topic,
        status=row.status,
        effective_date=row.effective_date,
        superseded_by=row.superseded_by,
        owner=row.owner,
        required_details=row.required_details or [],
        retriever_enabled=row.retriever_enabled,
    )
    if with_content and kb_doc:
        out.passages = [
            PassageOut(section=p.section, section_label=p.section_label, heading=p.heading, text=p.text, kind=p.kind)
            for p in kb_doc.passages
        ]
        out.conditions = [
            ConditionOut(id=c.id, when=c.when, text=c.text, key_phrase=c.key_phrase) for c in kb_doc.conditions
        ]
    return out


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    rows = db.scalars(select(Document).order_by(Document.topic, Document.effective_date)).all()
    return [_doc_out(r, with_content=False) for r in rows]


@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    row = db.get(Document, doc_id)
    if row is None:
        raise HTTPException(404, "Document not found")
    return _doc_out(row, with_content=True)


@router.post("/documents/{doc_id}/retriever", response_model=DocumentOut)
def set_retriever(doc_id: str, body: RetrieverToggle, db: Session = Depends(get_db)):
    """Switch a document on/off in OCBC AI's retriever (Q AI still sees it)."""
    row = db.get(Document, doc_id)
    if row is None:
        raise HTTPException(404, "Document not found")
    row.retriever_enabled = body.enabled
    row.retired_at = None if body.enabled else datetime.now()
    db.add(EventLog(actor="admin", event="retriever_toggled", data={"doc_id": doc_id, "enabled": body.enabled}))
    db.commit()
    return _doc_out(row, with_content=False)


@router.get("/conflicts", response_model=list[ConflictOut])
def list_conflicts(db: Session = Depends(get_db)):
    kb = get_kb()

    def label(doc_id: str) -> str:
        d = kb.doc(doc_id)
        return d.label if d else doc_id

    return [
        ConflictOut(
            id=c.id, topic=c.topic, field=c.field,
            doc_a=c.doc_a, doc_a_label=label(c.doc_a), value_a=c.value_a,
            doc_b=c.doc_b, doc_b_label=label(c.doc_b), value_b=c.value_b,
        )
        for c in db.scalars(select(Conflict)).all()
    ]


@router.get("/search", response_model=list[SearchHitOut])
def search(q: str, scope: str = "current", k: int = 5, db: Session = Depends(get_db)):
    """Debug search. scope=current (Q AI's view) or scope=ocbc (OCBC AI's view)."""
    kb = get_kb()
    doc_ids = kb.current_doc_ids() if scope == "current" else ocbc_enabled_doc_ids(db)
    out = []
    for h in kb.search(q, k, doc_ids):
        d = kb.doc(h.passage.doc_id)
        out.append(SearchHitOut(
            doc_id=d.id, doc_label=d.label, status=d.status,
            section_label=h.passage.section_label, text=h.passage.text, score=h.score,
        ))
    return out
