"""Local vector store: Chroma + sentence-transformers (all-MiniLM-L6-v2).

Works offline once the embedding model has been downloaded (first run only).
"""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.services.ingest import KBDocument, Passage

COLLECTION = "kb_passages"
# Hugging Face cache warns about symlinks on Windows; harmless, so silence it
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    # Imported lazily: torch takes a few seconds to load
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device="cpu")


@dataclass
class Hit:
    passage: Passage
    score: float  # cosine similarity, 1.0 = identical


class VectorStore:
    def __init__(self, persist_dir: Path, model_name: str):
        persist_dir.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name
        self.client = chromadb.PersistentClient(
            path=str(persist_dir), settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = None
        self.passages: dict[str, Passage] = {}

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = _load_model(self.model_name)
        return model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()

    def build(self, docs: list[KBDocument]) -> None:
        """(Re)index every passage of every document, superseded ones included."""
        try:
            self.client.delete_collection(COLLECTION)
        except Exception:
            pass  # first run: nothing to delete
        self.collection = self.client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

        passages = [p for d in docs for p in d.passages]
        meta = {d.id: d for d in docs}
        self.passages = {p.key: p for p in passages}
        self.collection.add(
            ids=[p.key for p in passages],
            embeddings=self.embed([f"{p.heading}. {p.text}" for p in passages]),
            documents=[p.text for p in passages],
            metadatas=[
                {"doc_id": p.doc_id, "section": p.section, "status": meta[p.doc_id].status, "kind": p.kind}
                for p in passages
            ],
        )

    def search(self, query: str, k: int, doc_ids: list[str] | None = None) -> list[Hit]:
        """Top-k passages for the query, optionally limited to some documents."""
        if self.collection is None or not query.strip() or doc_ids == []:
            return []
        where = {"doc_id": {"$in": list(doc_ids)}} if doc_ids is not None else None
        res = self.collection.query(
            query_embeddings=self.embed([query]),
            n_results=min(k, len(self.passages)),
            where=where,
        )
        hits = []
        for pid, dist in zip(res["ids"][0], res["distances"][0]):
            hits.append(Hit(self.passages[pid], round(1.0 - float(dist), 4)))
        return hits
