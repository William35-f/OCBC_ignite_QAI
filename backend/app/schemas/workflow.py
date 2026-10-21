"""Shapes of the workflow data, including every structured LLM output."""
from typing import Literal

from pydantic import BaseModel, Field

ClaimLabelName = Literal["Supported", "Partly supported", "Contradicted", "Unsupported"]
ALL_LABELS = ["Supported", "Partly supported", "Contradicted", "Unsupported", "Unable to verify"]


# --- Step 2: prompt check (LLM output) ------------------------------------------
class FollowUp(BaseModel):
    name: str = ""  # the required detail it fills, e.g. "payee_type"
    question: str
    options: list[str] = Field(min_length=1)


class PromptCheckResult(BaseModel):
    parts: list[str] = Field(min_length=1)
    topic: str = ""
    missing_details: list[FollowUp] = []
    assumptions: list[str] = []
    search_query: str
    # details already stated in the question, e.g. "new payee" -> {"payee_type": "New"}
    known_details: dict[str, str] = {}


# --- Step 4B: claim labelling (LLM output) ---------------------------------------
class ClaimLabel(BaseModel):
    id: int
    label: ClaimLabelName
    evidence_ids: list[int] = []
    reason: str = ""
    correction: str | None = None  # one-line correction when Contradicted


class ClaimLabels(BaseModel):
    labels: list[ClaimLabel]


# --- Stored / returned results -----------------------------------------------------
class Evidence(BaseModel):
    doc_id: str
    doc_label: str
    version: str
    status: str
    section: str
    section_label: str
    effective_date: str
    text: str
    score: float = 0.0


class ClaimResult(BaseModel):
    index: int = 0
    text: str
    label: str  # one of ALL_LABELS
    reason: str = ""
    correction: str | None = None
    evidence: list[Evidence] = []
    ignored_conflicting: list[str] = []  # older conflicting documents left out of the evidence


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    details: dict[str, str] = {}


class DetailsRequest(BaseModel):
    details: dict[str, str]
