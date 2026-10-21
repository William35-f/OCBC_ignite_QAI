"""The loaded knowledge base: documents, passages, conflict pairs and the vector store.

Both OCBC AI and Q AI read from this one object:
  - OCBC AI searches every document whose retriever switch is on
    (superseded ones included - that is the deliberate bug).
  - Q AI searches CURRENT documents only, and can read all metadata.
"""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Conflict, Document
from app.services.ingest import ConflictPair, KBDocument, Passage, compute_conflicts, load_documents
from app.services.vector_store import Hit, VectorStore


def _norm_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip().lower())


class KnowledgeBase:
    def __init__(self, docs: list[KBDocument], store: VectorStore):
        self.docs = {d.id: d for d in docs}
        self.conflicts: list[ConflictPair] = compute_conflicts(docs)
        self.store = store
        self._by_label = {_norm_label(d.label): d for d in docs}

    # --- lookups -------------------------------------------------------
    def doc(self, doc_id: str) -> KBDocument | None:
        return self.docs.get(doc_id)

    def doc_by_label(self, label: str) -> KBDocument | None:
        """Find a document from a citation label like 'Payments Procedure v2026'."""
        return self._by_label.get(_norm_label(label))

    def passage(self, doc_id: str, section: str) -> Passage | None:
        doc = self.docs.get(doc_id)
        if not doc:
            return None
        section = section.lstrip("§").strip().rstrip(".")
        exact = next((p for p in doc.passages if p.section == section), None)
        if exact:
            return exact
        # "§3" can mean all of §3.x: join the subsections
        subs = [p for p in doc.passages if p.section.startswith(section + ".")]
        if subs:
            return Passage(doc_id, section, subs[0].heading, " ".join(p.text for p in subs))
        return None

    def current_doc_ids(self) -> list[str]:
        return [d.id for d in self.docs.values() if d.status == "current"]

    def conflicts_for(self, doc_id: str) -> list[ConflictPair]:
        return [c for c in self.conflicts if doc_id in (c.doc_a, c.doc_b)]

    # --- search --------------------------------------------------------
    def search(self, query: str, k: int = 5, doc_ids: list[str] | None = None) -> list[Hit]:
        return self.store.search(query, k, doc_ids)

    def search_current(self, query: str, k: int = 3) -> list[Hit]:
        """Q AI's view: current documents only."""
        return self.store.search(query, k, self.current_doc_ids())


_kb: KnowledgeBase | None = None


def load_knowledge_base() -> KnowledgeBase:
    """Parse the markdown files, compute conflicts and (re)build the vector store."""
    global _kb
    docs = load_documents(settings.kb_dir)
    store = VectorStore(settings.chroma_dir, settings.embedding_model)
    store.build(docs)
    _kb = KnowledgeBase(docs, store)
    return _kb


def get_kb() -> KnowledgeBase:
    return _kb if _kb is not None else load_knowledge_base()


def sync_to_db(db: Session, kb: KnowledgeBase) -> None:
    """Upsert document rows (keeping the admin's retriever switch) and
    replace the conflicts table with the freshly computed pairs."""
    for d in kb.docs.values():
        row = db.get(Document, d.id)
        if row is None:
            row = Document(id=d.id, retriever_enabled=True)
            db.add(row)
        row.title, row.version, row.topic = d.title, d.version, d.topic
        row.status, row.effective_date, row.superseded_by = d.status, d.effective_date, d.superseded_by
        row.owner, row.required_details, row.path = d.owner, d.required_details, d.path
    db.query(Conflict).delete()
    for c in kb.conflicts:
        db.add(Conflict(**c.__dict__))
    db.commit()


def ocbc_enabled_doc_ids(db: Session) -> list[str]:
    """Documents OCBC AI's retriever may use (all of them, until an admin retires one)."""
    return list(db.scalars(select(Document.id).where(Document.retriever_enabled.is_(True))))
