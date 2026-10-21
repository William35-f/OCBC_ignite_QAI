"""Checks B and C, and all three together, on the demo answers (mock provider)."""
from app.services.checks.intent_check import run_intent_check
from app.services.checks.runner import question_figures, run_checks
from app.services.checks.source_check import label_claims, run_source_check

MR_TAN_Q = "What's the daily overseas transfer limit, and what do I need to check before processing?"
MR_TAN_PARTS = ["What's the daily overseas transfer limit?", "What do I need to check before processing?"]
MR_TAN_BAD = ("The daily overseas transfer limit is S$10,000. Verify the customer's ID and process the transfer. "
              "(Payments Procedure v2024, §3.1)")
MR_TAN_GOOD = ("For a new overseas payee, the daily limit is S$5,000. Verify the customer's ID and complete the "
               "scam-risk check before processing. (Payments Procedure v2026, §3.1, §4.1, §4.2)")
NEW = {"payee_type": "New"}


def types(flags):
    return {f["type"] for f in flags}


# --- B: sentence level -------------------------------------------------------
async def test_contradicted_claim_with_evidence_and_correction(kb):
    [r] = await label_claims(["The daily overseas transfer limit is S$10,000."], MR_TAN_Q, NEW)
    assert r.label == "Contradicted"
    assert r.evidence[0].doc_label == "Payments Procedure v2026" and r.evidence[0].section == "3.1"
    assert "S$5,000" in r.correction


async def test_existing_payee_makes_same_claim_supported(kb):
    [r] = await label_claims(["The daily overseas transfer limit is S$10,000."], MR_TAN_Q, {"payee_type": "Existing"})
    assert r.label == "Supported"


async def test_unable_to_verify_without_llm_below_threshold(kb):
    [r] = await label_claims(["Cryptocurrency transfers to a customer's wallet usually complete within an hour."], "q", {})
    assert r.label == "Unable to verify" and r.evidence == []


async def test_no_source_sentence_is_unable_to_verify(kb):
    [r] = await label_claims(["No approved source was found for cryptocurrency transfers."], "q", {})
    assert r.label == "Unable to verify"


async def test_older_conflicting_document_left_out_of_evidence(kb):
    [r] = await label_claims(["The limit for a new payee is S$5,000 per day."], "q", NEW)
    assert r.label == "Supported"
    assert all(e.doc_id != "branch-faq-2023" for e in r.evidence)
    assert r.ignored_conflicting == ["Branch FAQ 2023 §2"]


async def test_absence_claim_supported(kb):
    [r] = await label_claims(
        ["Arrival time depends on the receiving bank; the procedure does not state a fixed time."], "q", {})
    assert r.label == "Supported"


# --- B: counter-evidence ---------------------------------------------------------
async def test_missing_exception_found_in_current_replacement(kb):
    out = await run_source_check(MR_TAN_BAD, MR_TAN_Q, NEW, "overseas_transfers")
    missing = [e for e in out["exceptions"] if e["applies"] and not e["mentioned"]]
    assert [e["id"] for e in missing] == ["payments-procedure-v2026:C1"]
    assert "missing_exception" in types(out["flags"])


async def test_exception_mentioned_is_not_flagged(kb):
    out = await run_source_check(MR_TAN_GOOD, MR_TAN_Q, NEW, "overseas_transfers")
    assert "missing_exception" not in types(out["flags"])


async def test_conflict_lookup_older_side_is_warning(kb):
    out = await run_source_check("The limit for a new payee is S$10,000 per day. (Branch FAQ 2023, §2)", "q", NEW,
                                 "overseas_transfers")
    assert "conflict_older_source" in types(out["flags"])
    assert "contradicted" in types(out["flags"])  # the newer document wins


async def test_conflict_lookup_newer_side_is_only_a_note(kb):
    out = await run_source_check(MR_TAN_GOOD, MR_TAN_Q, NEW, "overseas_transfers")
    note = next(f for f in out["flags"] if f["type"] == "conflict_note")
    assert note["severity"] == "info"


async def test_yes_no_are_not_claims(kb):
    out = await run_source_check("Yes. No fee below S$1,000. (Payments Procedure v2026, §5)", "q", {}, None)
    assert out["skipped_sentences"] == [0] and len(out["claims"]) == 1


# --- C ----------------------------------------------------------------------------
async def test_part_two_partly_answered(kb):
    out = await run_intent_check(MR_TAN_PARTS, MR_TAN_BAD, MR_TAN_Q, NEW, "overseas_transfers")
    assert [p["status"] for p in out["parts"]] == ["answered", "partly"]
    assert "scam-risk check" in out["parts"][1]["reason"]


async def test_all_parts_answered(kb):
    out = await run_intent_check(MR_TAN_PARTS, MR_TAN_GOOD, MR_TAN_Q, NEW, "overseas_transfers")
    assert [p["status"] for p in out["parts"]] == ["answered", "answered"] and out["flags"] == []


async def test_no_source_answer_is_not_answered(kb):
    out = await run_intent_check(["Can I process crypto?"], "No approved source was found for this.", "q", {}, None)
    assert out["parts"][0]["status"] == "not_answered"


# --- A + B + C together ------------------------------------------------------------
async def test_mr_tan_red_with_all_expected_flags(kb):
    out = await run_checks(MR_TAN_BAD, MR_TAN_Q, NEW, MR_TAN_PARTS, "overseas_transfers")
    assert out["verdict"] == "Red"
    assert {"outdated_source", "contradicted", "missing_exception", "part_partly_answered"} <= types(out["flags"])
    assert [s["label"] for s in out["sentences"]] == ["Contradicted", "Supported"]


async def test_mr_tan_corrected_is_green(kb):
    out = await run_checks(MR_TAN_GOOD, MR_TAN_Q, NEW, MR_TAN_PARTS, "overseas_transfers")
    assert out["verdict"] == "Green", out["flags"]


async def test_amber_answer(kb):
    out = await run_checks(
        "Transfers usually arrive within 1 business day. There is no fee for transfers below S$1,000. "
        "(Payments Procedure v2026, §5)",
        "How long does an overseas transfer take, and is there a fee?", {},
        ["How long does an overseas transfer take?", "Is there a fee?"], "overseas_transfers")
    assert out["verdict"] == "Amber"
    assert [s["label"] for s in out["sentences"]] == ["Unsupported", "Supported"]


def test_question_figures_only_from_parts():
    # The assumed S$10,000 is not a part, so it is still checked
    assert question_figures(["Can I send S$8,000 to a new payee?"]) == ["s$8,000"]
