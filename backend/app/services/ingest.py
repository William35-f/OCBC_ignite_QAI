"""Parse knowledge-base markdown files and compute conflict pairs.

File format (see data/knowledge_base/*.md):
  - YAML front matter with id, title, topic, version, effective_date, status,
    superseded_by, owner, required_details, fields
  - numbered sections:   ## §3 Limits  /  ### §3.1 Overseas transfer limit
  - a "## Conditions and exceptions" section with one condition per line:
        - [C1] (when: payee_type=new) A **scam-risk check** is required ...
    "when" says which questions the condition applies to; the **bold** text is
    the key phrase an answer must mention.
"""
import re
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

import yaml

SECTION_RE = re.compile(r"^#{2,3}\s+§\s?([\d.]+)\s+(.*)$")
CONDITIONS_RE = re.compile(r"^##\s+Conditions and exceptions", re.IGNORECASE)
CONDITION_LINE_RE = re.compile(r"^-\s*\[(C\d+)\]\s*\(when:\s*([^)]*)\)\s*(.*)$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
SECTION_REF_RE = re.compile(r"\(see §\s?([\d.]+)\)")


@dataclass
class Passage:
    doc_id: str
    section: str  # "3.1", or "C1" for a condition
    heading: str
    text: str
    kind: str = "section"  # section | condition

    @property
    def section_label(self) -> str:
        return f"§{self.section}" if self.kind == "section" else f"Conditions and exceptions ({self.section})"

    @property
    def key(self) -> str:
        return f"{self.doc_id}#{self.section}"


@dataclass
class Condition:
    id: str
    when: str  # e.g. "payee_type=new" or "mentions=stolen|police"
    text: str  # plain text, bold markers removed
    key_phrase: str  # the **bold** part
    section_ref: str | None = None  # e.g. "4.2" when the text says "(see §4.2)"

    def applies(self, question: str, details: dict) -> bool:
        """Does this condition apply to the question? Rules are separated by ';'
        and any matching rule is enough."""
        q = question.lower()
        norm_details = {k: str(v).lower() for k, v in (details or {}).items()}
        for rule in self.when.split(";"):
            name, _, value = rule.strip().partition("=")
            name, value = name.strip(), value.strip().lower()
            if name == "always":
                return True
            if name == "mentions":
                if any(term and term in q for term in value.split("|")):
                    return True
            elif norm_details.get(name) == value:
                return True
        return False


@dataclass
class KBDocument:
    id: str
    title: str
    topic: str
    version: str
    effective_date: str
    status: str
    superseded_by: str | None
    owner: str
    required_details: list[dict]
    fields: dict[str, str]
    path: str
    passages: list[Passage] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)

    @property
    def label(self) -> str:
        """How OCBC AI cites the document, e.g. 'Payments Procedure v2026'."""
        return f"{self.title} {self.version}"

    @property
    def conditions_text(self) -> str:
        return "\n".join(f"[{c.id}] (applies when: {c.when}) {c.text}" for c in self.conditions)


@dataclass
class ConflictPair:
    topic: str
    field: str
    doc_a: str  # the newer document (later effective date)
    value_a: str
    doc_b: str
    value_b: str


def _split_front_matter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        raise ValueError("missing YAML front matter")
    _, fm, body = raw.split("---", 2)
    return yaml.safe_load(fm) or {}, body


def parse_document(path: Path) -> KBDocument:
    meta, body = _split_front_matter(path.read_text(encoding="utf-8"))
    doc = KBDocument(
        id=meta["id"],
        title=meta["title"],
        topic=meta["topic"],
        version=str(meta["version"]),
        effective_date=str(meta["effective_date"]),
        status=meta["status"],
        superseded_by=meta.get("superseded_by"),
        owner=meta.get("owner", ""),
        required_details=meta.get("required_details") or [],
        fields={k: str(v) for k, v in (meta.get("fields") or {}).items()},
        path=path.name,
    )

    current: Passage | None = None
    in_conditions = False

    def flush() -> None:
        # Parent headings like "## §3 Limits" have no text of their own: skip them
        if current is not None and current.text.strip():
            current.text = current.text.strip()
            doc.passages.append(current)

    for line in body.splitlines():
        if m := SECTION_RE.match(line):
            flush()
            current = Passage(doc.id, m.group(1).rstrip("."), m.group(2).strip(), "")
            in_conditions = False
        elif CONDITIONS_RE.match(line):
            flush()
            current = None
            in_conditions = True
        elif in_conditions and (m := CONDITION_LINE_RE.match(line.strip())):
            raw_text = m.group(3).strip()
            bold = BOLD_RE.search(raw_text)
            ref = SECTION_REF_RE.search(raw_text)
            cond = Condition(
                id=m.group(1),
                when=m.group(2).strip(),
                text=BOLD_RE.sub(r"\1", raw_text),
                key_phrase=bold.group(1) if bold else "",
                section_ref=ref.group(1) if ref else None,
            )
            doc.conditions.append(cond)
            # Conditions are also searchable passages
            doc.passages.append(Passage(doc.id, cond.id, "Conditions and exceptions", cond.text, "condition"))
        elif current is not None and not line.startswith("#"):
            current.text += line.strip() + " "
    flush()
    return doc


def load_documents(kb_dir: Path) -> list[KBDocument]:
    return [parse_document(p) for p in sorted(kb_dir.glob("*.md"))]


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _in_same_version_chain(a: KBDocument, b: KBDocument, by_id: dict[str, KBDocument]) -> bool:
    """True if one document supersedes the other (directly or via a chain)."""
    for start, target in ((a, b), (b, a)):
        seen, cur = set(), start
        while cur and cur.superseded_by and cur.id not in seen:
            seen.add(cur.id)
            if cur.superseded_by == target.id:
                return True
            cur = by_id.get(cur.superseded_by)
    return False


def compute_conflicts(docs: list[KBDocument]) -> list[ConflictPair]:
    """Conflict = same topic, same field, different value.

    Run once at load time. Skipped on purpose:
      - superseded documents (the source_current rule already catches them)
      - old/new versions of the same procedure (that is a version change, not a conflict)
    """
    by_id = {d.id: d for d in docs}
    live = [d for d in docs if d.status == "current"]
    pairs: list[ConflictPair] = []
    for a, b in combinations(sorted(live, key=lambda d: d.id), 2):
        if a.topic != b.topic or _in_same_version_chain(a, b, by_id):
            continue
        newer, older = (a, b) if a.effective_date >= b.effective_date else (b, a)
        for fld in sorted(set(a.fields) & set(b.fields)):
            if _norm(newer.fields[fld]) != _norm(older.fields[fld]):
                pairs.append(
                    ConflictPair(a.topic, fld, newer.id, newer.fields[fld], older.id, older.fields[fld])
                )
    return pairs
