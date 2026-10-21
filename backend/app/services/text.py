"""Plain-text helpers shared by the checks: sentences, citations, figures, keywords."""
import re
from dataclasses import dataclass, field

# --- citations: (Payments Procedure v2026, §3.1, §4.2) or (A v1, §2; B v2, §3) ---
CITATION_RE = re.compile(r"\(([^()]*§[^()]*)\)")
SECTION_IN_CITATION_RE = re.compile(r"§\s?([0-9][0-9A-Za-z.]*)")


@dataclass
class Citation:
    doc_label: str
    sections: list[str]


def parse_citations(text: str) -> list[Citation]:
    out = []
    for inner in CITATION_RE.findall(text):
        for chunk in inner.split(";"):
            label, _, rest = chunk.partition(",")
            sections = [s.rstrip(".") for s in SECTION_IN_CITATION_RE.findall(rest)]
            if label.strip() and sections:
                out.append(Citation(label.strip(), sections))
    return out


def strip_citations(text: str) -> str:
    return re.sub(r"\s+", " ", CITATION_RE.sub("", text)).strip()


# --- sentences ---------------------------------------------------------------
_ABBREV = {"p.a.": "p<dot>a<dot>", "e.g.": "e<dot>g<dot>", "i.e.": "i<dot>e<dot>"}


@dataclass
class Sentence:
    index: int
    text: str  # without citations
    raw: str  # as written, citations included
    citations: list[Citation] = field(default_factory=list)


def split_sentences(answer: str) -> list[Sentence]:
    """Split an answer into sentences. A citation standing on its own after a
    full stop, e.g. "... the transfer. (Doc v1, §3)", belongs to the sentence before."""
    text = answer.strip()
    for k, v in _ABBREV.items():
        text = text.replace(k, v)
    pieces = [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z(\"“])", text) if p.strip()]
    sentences: list[Sentence] = []
    for piece in pieces:
        for k, v in _ABBREV.items():
            piece = piece.replace(v, k)
        cites = parse_citations(piece)
        body = strip_citations(piece)
        if sentences and cites and not re.search(r"[A-Za-z0-9]", body.strip(".")):
            # citation-only piece: attach to the previous sentence
            prev = sentences[-1]
            prev.citations.extend(cites)
            prev.raw = f"{prev.raw} {piece}"
            continue
        sentences.append(Sentence(len(sentences), body, piece, cites))
    return sentences


# --- figures: amounts, percentages, dates, numbers ------------------------------
_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
FIGURE_RES = [
    ("money", re.compile(r"S\$\s?\d[\d,]*(?:\.\d+)?", re.I)),
    ("percent", re.compile(r"\d+(?:\.\d+)?\s?%")),
    ("date", re.compile(rf"\b\d{{4}}-\d{{2}}-\d{{2}}\b|\b\d{{1,2}} (?:{_MONTHS}) \d{{4}}\b")),
    ("number", re.compile(r"(?<![\w$.,])\d+(?:[.,]\d+)*(?![\w%])")),
]


def extract_figures(text: str) -> list[tuple[str, str]]:
    """Every amount, percentage, date and number, as (kind, normalised value)."""
    found: list[tuple[str, str]] = []
    taken: list[tuple[int, int]] = []
    for kind, rx in FIGURE_RES:
        for m in rx.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue  # already part of a longer figure
            taken.append((m.start(), m.end()))
            found.append((kind, normalise_figure(m.group())))
    return found


def normalise_figure(value: str) -> str:
    v = value.lower().replace(" ", "")
    return v.rstrip(".,")


# --- keywords -------------------------------------------------------------------
STOPWORDS = set(
    """a an the is are was were be been being to of for and or in on at by with from as it its this that these those
    there their they them he she we you your i me my our can could do does did should must will would may might shall
    what what's whats how which when who whom why where if then than so such into about per before after also only
    just please tell need needs have has had any each usually generally""".split()
)
SYNONYMS = {"daily": "day", "identity": "id", "charge": "fee", "charges": "fee", "first-time": "new"}


def stem(word: str) -> str:
    word = SYNONYMS.get(word, word)
    if word.endswith("'s"):
        word = word[:-2]
    for suffix in ("ing", "ed"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def keywords(text: str) -> set[str]:
    """Content words (lower-cased, crudely stemmed, stopwords removed)."""
    tokens = re.findall(r"s\$[\d,.]+|\d+(?:\.\d+)?%|[a-z][a-z'-]*[a-z]|[a-z]|\d+", text.lower())
    return {stem(t.strip(".,")) for t in tokens if t not in STOPWORDS}


ABSENCE_RE = re.compile(
    r"\b(does not (?:state|specify|say|mention)|is not (?:stated|specified)|no (?:fixed|stated|set) \w+)\b", re.I
)
# Sentences where the answer itself says there is no source (Q AI cannot verify these)
NO_SOURCE_RE = re.compile(
    r"\bno approved (?:source|procedure)\b|\bcould not find\b|\bno (?:current )?(?:source|procedure) (?:was found|covers)\b",
    re.I,
)
