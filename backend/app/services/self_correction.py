"""Step 5b - self-correction (Amber only, ONE retry at most).

Q AI never rewrites the answer itself. It sends OCBC AI its flags plus the
correct passages as feedback, and OCBC AI answers again. The original answer
stays saved; the retry is stored separately and checked again from scratch.
"""
import difflib

from app.services.text import split_sentences

# Flags worth telling OCBC AI about (info notes are not problems)
FEEDBACK_TYPES = {
    "unsupported": "has no supporting passage in the current procedures",
    "unable_to_verify": "could not be checked against any approved source",
    "partly_supported": "is only partly supported by the current procedures",
    "figure_mismatch": "contains a figure that is not in the cited section",
    "no_citation": None,
    "citation_not_found": None,
    "conflict_older_source": None,
    "part_partly_answered": None,
    "part_not_answered": None,
}


def build_feedback(checks: dict) -> tuple[str, list[str], list[dict]]:
    """Turn the Amber flags into feedback for OCBC AI.

    Returns (feedback text, flagged sentences, correct passages)."""
    sentences = {s["index"]: s for s in checks["sentences"]}
    lines, flagged = [], []
    for f in checks["flags"]:
        if f["type"] not in FEEDBACK_TYPES:
            continue
        idx = f.get("sentence_index")
        problem = FEEDBACK_TYPES[f["type"]]
        if idx is not None and problem and idx in sentences:
            text = sentences[idx]["text"]
            if text not in flagged:
                flagged.append(text)
            lines.append(f"- The claim '{text}' {problem}.")
        else:
            lines.append(f"- {f['message']}")

    # The correct passages: everything Q AI found supporting the answer
    passages, seen = [], set()
    for s in checks["sentences"]:
        for e in s["evidence"]:
            key = (e["doc_id"], e["section"])
            if s["label"] in ("Supported", "Partly supported") and key not in seen:
                seen.add(key)
                passages.append({"label": e["doc_label"], "section": e["section_label"], "text": e["text"]})

    text = "Q AI checked your answer and found these problems:\n" + "\n".join(dict.fromkeys(lines))
    if passages:
        text += "\n\nCorrect passages from current procedures:\n" + "\n".join(
            f"- ({p['label']}, {p['section']}) {p['text']}" for p in passages
        )
    text += (
        "\n\nAnswer again using only the cited procedures. Remove anything they do not state, and say plainly "
        "when the procedures do not cover something. If no approved source covers the question, say so."
    )
    return text, flagged, passages


def what_changed(original: str, retry: str) -> list[dict]:
    """A simple sentence-level diff of the two answers for the "What changed" note."""
    a = [s.raw for s in split_sentences(original)]
    b = [s.raw for s in split_sentences(retry)]
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            out += [{"type": "same", "text": t} for t in a[i1:i2]]
            continue
        out += [{"type": "removed", "text": t} for t in a[i1:i2]]
        out += [{"type": "added", "text": t} for t in b[j1:j2]]
    return out
