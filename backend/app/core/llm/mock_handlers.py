"""Rule-based mock outputs for each LLM task (no API key, no internet).

- prompt_check : splits the question, finds missing required details, pulls out assumptions
- ocbc_answer  : scripted answers for the demo scenarios, chosen by WHAT THE RETRIEVER RETURNED
                 (so retiring a document really changes the answer), plus a naive generic answer
- label_claims : compares figures and keywords between each claim and its evidence passages
- missing_exceptions : a condition applies by its "when" rule; it is mentioned if its key phrase is in the answer
- intent_check : a part is addressed if an answer sentence is semantically close to it (local embeddings);
                 a "what do I need to do/check" part is partly answered if an applicable condition is missing
"""
import re

from app.core.llm.mock import mock_handler
from app.services.text import ABSENCE_RE, NO_SOURCE_RE, STOPWORDS, extract_figures, keywords, split_sentences

V2024, V2026 = "payments-procedure-v2024", "payments-procedure-v2026"
CARD = "card-replacement-v2025"


# =============================================================================
# Step 2: prompt check
# =============================================================================
PART_SPLIT_RE = re.compile(
    r",?\s+and\s+(?=(?:what|how|is|are|do|does|can|which|when|where|who|why|should|will)\b)|(?<=\?)\s+", re.I
)
# "Since <assumption>, <question>" - the comma must not be inside a number like S$10,000
ASSUMPTION_RE = re.compile(r"^(?:since|given that|as|because|assuming)\s+(.+?),\s+(?!\d)(.+)$", re.I)


def _tidy_question(text: str) -> str:
    text = text.strip().strip(",").strip()
    text = text[0].upper() + text[1:] if text else text
    return text if text.endswith("?") else text.rstrip(".") + "?"


def _detail_in_question(q: str, name: str, option: str) -> bool:
    """Is this option stated in the question? e.g. 'new' near 'payee' for payee_type=New."""
    noun = name.split("_")[0]
    for term in (t.strip().lower() for t in option.split("/")):
        if re.search(rf"\b{re.escape(term)}\b[\w\s-]{{0,20}}\b{re.escape(noun)}", q):
            return True
        if len(term) >= 7 and re.search(rf"\b{re.escape(term)}\b", q):
            return True
    return False


def _search_query(body: str, details: dict) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9$%'-]+(?:,\d{3})*", body) if w.lower() not in STOPWORDS]
    query = " ".join(words)
    for name, value in details.items():
        phrase = f"{value.lower()} {name.split('_')[0]}"
        if phrase not in query.lower():
            query += f" {phrase}"
    return query.strip()


@mock_handler("prompt_check")
def prompt_check(p: dict) -> dict:
    question = p["question"].strip()
    q = question.lower()
    details = p.get("details") or {}
    docs = p.get("candidate_documents") or []
    top = docs[0] if docs else None
    required = p.get("required_details") or []

    # Assumptions: "Since the limit is S$10,000, can I ...?"
    assumptions, body = [], question
    if m := ASSUMPTION_RE.match(question):
        clause, body = m.group(1).strip(), m.group(2).strip()
        claim = clause[0].upper() + clause[1:]
        if re.search(r"\bnew payee", q) and "payee" not in clause.lower():
            claim += " for a new payee"
        assumptions.append(claim.rstrip(".") + ".")

    parts = [_tidy_question(x) for x in PART_SPLIT_RE.split(body) if x and x.strip()]

    known, missing = {}, []
    for rd in required:
        for opt in rd.get("options", []):
            if _detail_in_question(q, rd["name"], opt):
                known[rd["name"]] = opt
        if rd["name"] in details or rd["name"] in known:
            continue
        # whole words only: "process" should not match "processed"
        if any(re.search(rf"\b{re.escape(term)}\b", q) for term in rd.get("needed_when", [])):
            missing.append({"name": rd["name"], "question": rd["question"], "options": rd["options"]})

    return {
        "parts": parts or [_tidy_question(question)],
        "topic": top["topic"] if top else "general",
        "missing_details": missing[: int(p.get("max_followups", 2))],
        "assumptions": assumptions,
        "search_query": _search_query(body, {**details, **known}),
        "known_details": known,
    }


# =============================================================================
# Step 3: OCBC AI answer
# =============================================================================
def _has(passages: list[dict], doc_id: str, section: str | None = None) -> bool:
    return any(x["doc_id"] == doc_id and (section is None or x["section"] == section) for x in passages)


def _money_to_int(text: str) -> int:
    return int(re.sub(r"[^\d]", "", text))


@mock_handler("ocbc_answer")
def ocbc_answer(p: dict) -> str:
    q = p["question"].lower()
    passages = p.get("passages") or []
    details = {k: str(v).lower() for k, v in (p.get("details") or {}).items()}
    new_payee = details.get("payee_type") == "new"

    if p.get("feedback"):
        return _retry_answer(p)

    # Scenario 5: nothing in the knowledge base covers crypto
    if re.search(r"crypto|bitcoin|digital token", q):
        return "Cryptocurrency transfers to a customer's wallet usually complete within an hour."

    # Scenario 1 (Mr Tan): limit + what to check before processing
    if "limit" in q and re.search(r"check|before processing|verify", q):
        if _has(passages, V2024, "3.1"):  # the retriever returned the superseded procedure first
            return (
                "The daily overseas transfer limit is S$10,000. Verify the customer's ID and process the "
                "transfer. (Payments Procedure v2024, §3.1)"
            )
        if _has(passages, V2026):
            if new_payee:
                return (
                    "For a new overseas payee, the daily limit is S$5,000. Verify the customer's ID and complete "
                    "the scam-risk check before processing. (Payments Procedure v2026, §3.1, §4.1, §4.2)"
                )
            return (
                "For an existing payee, the daily overseas transfer limit is S$10,000. Verify the customer's ID "
                "before processing. (Payments Procedure v2026, §3.1, §4.1)"
            )

    # Scenario 4: "Since the limit is S$10,000, can I send S$8,000 to a new payee?"
    amounts = re.findall(r"s\$\s?[\d,]+", q)
    if amounts and "payee" in q and re.search(r"\bsend|transfer", q):
        amount = amounts[-1].upper().replace(" ", "")
        if _has(passages, V2024, "3.1"):
            ok = _money_to_int(amount) <= 10000
            verb = "within" if ok else "above"
            return (
                f"{'Yes' if ok else 'No'}. The daily overseas transfer limit is S$10,000, so {amount} is {verb} "
                "the limit. (Payments Procedure v2024, §3.1)"
            )
        if _has(passages, V2026):
            limit = 5000 if new_payee else 10000
            ok = _money_to_int(amount) <= limit
            who = "New payees are" if new_payee else "Existing payees are"
            text = (
                f"{'Yes' if ok else 'No'}. {who} limited to S${limit:,} per day, so {amount} is "
                f"{'within' if ok else 'above'} the limit."
            )
            if new_payee:
                text += " A scam-risk check is required before processing any transfer to a first-time overseas payee."
                return text + " (Payments Procedure v2026, §3.1, §4.2)"
            return text + " (Payments Procedure v2026, §3.1)"

    # Scenario 6 (still Amber after the retry): card delivery time + fee. The card
    # procedure only says the card is mailed; it states no delivery time.
    if "card" in q and re.search(r"how long|arrive", q) and _has(passages, CARD):
        return (
            "A replacement card arrives within 5 working days. A replacement fee of S$15 is charged to the "
            "customer's account. (Card Replacement Procedure v2025, §3)"
        )

    # Scenario 2 (Amber): arrival time + fee. No document states an arrival time.
    if re.search(r"how long|arrive|take", q) and "fee" in q and _has(passages, V2026, "5"):
        return (
            "Transfers usually arrive within 1 business day. There is no fee for transfers below S$1,000. "
            "(Payments Procedure v2026, §5)"
        )

    return _generic_answer(p)


def _retry_answer(p: dict) -> str:
    """Step 5b: OCBC AI answers again after Q AI's feedback."""
    q = p["question"].lower()
    previous = p.get("previous_answer") or ""
    flagged = set(p.get("flagged_sentences") or [])

    # Scenario 5: still no approved source
    if re.search(r"crypto|bitcoin|digital token", q):
        return "No approved source was found for cryptocurrency transfers, so I cannot confirm whether they are allowed."

    # Scenario 2: drop the made-up arrival time, keep the supported fee
    if previous.startswith("Transfers usually arrive within 1 business day."):
        return (
            "Arrival time depends on the receiving bank; the procedure does not state a fixed time. "
            "There is no fee for transfers below S$1,000. (Payments Procedure v2026, §5)"
        )

    # Scenario 6: OCBC AI drops the made-up "5 working days" but still guesses a
    # delivery time, so the retry is only partly supported -> still Amber -> review
    if previous.startswith("A replacement card arrives within 5 working days."):
        return (
            "The replacement card is mailed to the customer's registered address and usually arrives within one "
            "week, or two weeks for overseas addresses. A replacement fee of S$15 is charged to the customer's "
            "account. (Card Replacement Procedure v2025, §3, §4)"
        )

    # Generic: keep only the sentences Q AI did not flag
    kept = [s.raw for s in split_sentences(previous) if s.text not in flagged]
    kept_text = " ".join(kept)
    if not kept or not re.search(r"[A-Za-z]{3,}", re.sub(r"\([^)]*§[^)]*\)", "", kept_text)):
        return "No approved source was found for this question in the procedures I can search."
    # The citation may have sat on a removed sentence: re-attach it
    citations = re.findall(r"\([^()]*§[^()]*\)", previous)
    if citations and not re.search(r"\([^()]*§[^()]*\)", kept_text):
        kept_text = f"{kept_text} {citations[-1]}"
    return kept_text


def _generic_answer(p: dict) -> str:
    """A naive RAG answer: for each question part, quote the best matching passage."""
    all_passages = p.get("passages") or []
    doc_rank = {}
    for x in all_passages:  # rank documents by their best hit
        doc_rank.setdefault(x["doc_id"], len(doc_rank))
    passages = [x for x in all_passages if x["kind"] == "section" and x["heading"].lower() != "purpose"]
    if not passages or max(x["score"] for x in passages) < 0.35:
        return "No approved source was found for this question in the procedures I can search."
    sentences, used = [], set()
    for part in p.get("parts") or [p["question"]]:
        pk = keywords(part)
        best = max(
            passages,
            key=lambda x: (len(pk & keywords(f"{x['heading']} {x['text']}")), -doc_rank[x["doc_id"]], x["score"]),
        )
        key = (best["doc_id"], best["section"])
        if key in used:
            continue
        used.add(key)
        text = best["text"].rstrip(".")
        sentences.append(f"{text}. ({best['label']}, §{best['section']})")
    return " ".join(sentences)


# =============================================================================
# Step 4B: claim labelling
# =============================================================================
def _clauses(text: str) -> list[str]:
    """'Limit: A; B' -> ['Limit: A', 'Limit: B'] so each clause keeps its subject."""
    head, sep, rest = text.partition(":")
    if sep and ";" in rest and len(head) < 60:
        return [f"{head.strip()}: {r.strip().rstrip('.')}" for r in rest.split(";") if r.strip()]
    # Split on ";" and on sentence ends, but not inside "p.a." / "e.g." / "i.e."
    protected = re.sub(r"\b(p\.a|e\.g|i\.e)\.", lambda m: m.group(0).replace(".", "<dot>"), text)
    return [s.replace("<dot>", ".").strip() for s in re.split(r";|(?<=\.)\s+", protected) if s.strip()]


LABEL_RANK = {"Supported": 0, "Partly supported": 1, "Unsupported": 2, "Contradicted": 3}
SAME_SUBJECT_MIN = 3
NEGATIONS = {"no", "not", "never", "cannot", "can't", "won't", "isn't", "aren't", "don't", "doesn't"}


def _label_one(claim: dict, detail_words: set[str], ignore: set[str]) -> dict:
    text, evidence = claim["text"], claim["evidence"]
    all_ids = [e["id"] for e in evidence]

    def result(label: str, reason: str, ids=None, correction=None) -> dict:
        return {"id": claim["id"], "label": label, "evidence_ids": ids or all_ids, "reason": reason, "correction": correction}

    if ABSENCE_RE.search(text):
        return result("Supported", "None of the current passages states this, which matches the claim.")

    # "Limit: A for X; B for Y" states two facts: check each clause on its own
    # (each clause names its own case, so the employee's details are not mixed in)
    parts = _clauses(text)
    if len(parts) > 1 and len([p for p in parts if extract_figures(p)]) > 1:
        labelled = [_label_one({**claim, "text": p}, set(), ignore) for p in parts]
        worst = max(labelled, key=lambda r: LABEL_RANK[r["label"]])
        if worst["label"] == "Supported":
            ids = sorted({i for r in labelled for i in r["evidence_ids"]})
            return result("Supported", "Every part of this sentence matches the current procedure.", ids)
        return worst

    claim_words = keywords(text)
    figures = [f for f in extract_figures(text) if f[1] not in ignore]
    fig_values = {v for _, v in figures}
    match_words = {w for w in claim_words if not extract_figures(w)} | detail_words

    # Pick the evidence clause that best matches the claim's wording (not its figures)
    clauses = [(e, c) for e in evidence for c in _clauses(e["text"])]
    best_e, best_c = max(clauses, key=lambda ec: len(match_words & keywords(ec[1])))

    if figures:
        best_figs = {v for _, v in extract_figures(best_c)}
        if fig_values <= best_figs:
            return result("Supported", f"The figures match {best_e['doc_label']} {best_e['section_label']}.", [best_e["id"]])
        kinds = {k for k, _ in figures}
        same_kind = {v for k, v in extract_figures(best_c) if k in kinds}
        # A different figure only contradicts the claim if the clause is about the same
        # thing: at least 3 shared content words (an ATM limit is not a transfer limit)
        same_subject = len((claim_words - {v for _, v in figures}) & keywords(best_c)) >= SAME_SUBJECT_MIN
        if same_kind and same_subject and not (fig_values & best_figs):
            tail = best_c.split(":", 1)[-1].strip()
            note = (
                f"Note: {best_e['doc_label']} {best_e['section_label']} says {tail}, "
                f"not {', '.join(sorted(v.upper() for v in fig_values))}."
            )
            return result(
                "Contradicted",
                f"{best_e['doc_label']} {best_e['section_label']} states a different figure for this case.",
                [best_e["id"]],
                note,
            )
        all_figs = {v for e in evidence for _, v in extract_figures(e["text"])}
        if fig_values & all_figs:
            return result("Partly supported", "Some figures appear in the evidence, but not all of them.")
        return result("Unsupported", "The evidence is on this topic but does not state these figures.")

    # No figures: how much of the sentence's wording is in the evidence?
    # Only passages sharing at least 2 content words count as the evidence used.
    used = [e for e in evidence if len(claim_words & keywords(e["text"])) >= 2] or evidence
    used_ids = [e["id"] for e in used]
    evidence_words = set().union(*(keywords(e["text"]) for e in used))
    coverage = len(claim_words & evidence_words) / max(1, len(claim_words))

    # Polarity: same wording, but one side says "no" / "not" ("No interest is paid"
    # vs "Interest of 0.05% p.a. is paid") -> the evidence says the opposite
    closest = max(used, key=lambda e: len(claim_words & keywords(e["text"])))
    overlap = len((claim_words - NEGATIONS) & keywords(closest["text"])) / max(1, len(claim_words - NEGATIONS))
    if overlap >= 0.5 and bool(claim_words & NEGATIONS) != bool(keywords(closest["text"]) & NEGATIONS):
        return result(
            "Contradicted",
            f"{closest['doc_label']} {closest['section_label']} says the opposite.",
            [closest["id"]],
            f"Note: {closest['doc_label']} {closest['section_label']} says: “{closest['text']}”",
        )

    if coverage >= 0.6:
        return result("Supported", "The evidence states this.", used_ids)
    if coverage >= 0.3:
        return result("Partly supported", "Only part of this sentence is in the evidence.", used_ids)
    return result("Unsupported", "The evidence is on this topic but does not state this.", used_ids)


@mock_handler("label_claims")
def label_claims(p: dict) -> dict:
    detail_words = keywords(" ".join(str(v) for v in (p.get("details") or {}).values()))
    ignore = set(p.get("ignore_figures") or [])
    return {"labels": [_label_one(c, detail_words, ignore) for c in p["claims"]]}


# =============================================================================
# Step 4B: missing exceptions
# =============================================================================
def _plain(text: str) -> str:
    return re.sub(r"[\s-]+", " ", text.lower()).strip()


@mock_handler("missing_exceptions")
def missing_exceptions(p: dict) -> dict:
    answer = _plain(p["answer"])
    out = []
    for c in p["conditions"]:
        mentioned = bool(c["key_phrase"]) and _plain(c["key_phrase"]) in answer
        reason = "Applies to this question." if c["applies_by_rule"] else "Does not apply to this question."
        out.append({"id": c["id"], "applies": c["applies_by_rule"], "mentioned": mentioned, "reason": reason})
    return {"conditions": out}


# =============================================================================
# Step 4C: intent check
# =============================================================================
PROCEDURAL_RE = re.compile(
    r"\b(need to|have to|must i|should i|check|steps?|before processing|what do i do|how do i|documents?|requirements?)\b",
    re.I,
)
ADDRESSED_MIN = 0.35  # cosine similarity between a part and its closest answer sentence


@mock_handler("intent_check")
def intent_check(p: dict) -> dict:
    from app.services.knowledge_base import get_kb  # local embeddings, no LLM

    parts = p["parts"]
    sentences = [s.text for s in split_sentences(p["answer"]) if not NO_SOURCE_RE.search(s.text)]
    answer = _plain(p["answer"])
    out = []
    if not sentences:
        return {"parts": [{"part": x, "status": "not_answered", "reason": "The answer says no approved source was found."}
                          for x in parts]}
    vectors = get_kb().store.embed(parts + sentences)
    for n, part in enumerate(parts):
        sims = [sum(a * b for a, b in zip(vectors[n], vectors[len(parts) + m])) for m in range(len(sentences))]
        if max(sims) < ADDRESSED_MIN:
            out.append({"part": part, "status": "not_answered", "reason": "No sentence in the answer addresses it."})
            continue
        missing = [c["key_phrase"] for c in p.get("applicable_conditions") or []
                   if c["key_phrase"] and _plain(c["key_phrase"]) not in answer]
        if PROCEDURAL_RE.search(part) and missing:
            out.append({"part": part, "status": "partly", "reason": f"It leaves out: {', '.join(missing)}."})
        else:
            out.append({"part": part, "status": "answered", "reason": "The answer addresses this part."})
    return {"parts": out}
