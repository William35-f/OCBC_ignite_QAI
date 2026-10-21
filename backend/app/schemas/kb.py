"""API shapes for the knowledge base and settings pages."""
from pydantic import BaseModel


class PassageOut(BaseModel):
    section: str
    section_label: str
    heading: str
    text: str
    kind: str


class ConditionOut(BaseModel):
    id: str
    when: str
    text: str
    key_phrase: str


class DocumentOut(BaseModel):
    id: str
    label: str
    title: str
    version: str
    topic: str
    status: str
    effective_date: str
    superseded_by: str | None
    owner: str
    required_details: list[dict]
    retriever_enabled: bool
    passages: list[PassageOut] = []
    conditions: list[ConditionOut] = []


class ConflictOut(BaseModel):
    id: int
    topic: str
    field: str
    doc_a: str
    doc_a_label: str
    value_a: str
    doc_b: str
    doc_b_label: str
    value_b: str


class SearchHitOut(BaseModel):
    doc_id: str
    doc_label: str
    status: str
    section_label: str
    text: str
    score: float


class RetrieverToggle(BaseModel):
    enabled: bool


class SettingsUpdate(BaseModel):
    llm_provider: str | None = None
    similarity_threshold: float | None = None
    max_followups: int | None = None
