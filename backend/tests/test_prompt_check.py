"""Step 2 - prompt check (mock provider)."""
from app.services.demo import SCENARIOS
from app.services.prompt_check import run_prompt_check

Q = {s["id"]: s["question"] for s in SCENARIOS}


async def test_mr_tan_split_into_two_parts_and_asks_payee_type(kb):
    pc = await run_prompt_check(Q["red"], {})
    assert pc["parts"] == ["What's the daily overseas transfer limit?", "What do I need to check before processing?"]
    assert [m["question"] for m in pc["missing_details"]] == ["Is this payee new or existing?"]
    assert pc["missing_details"][0]["options"] == ["New", "Existing"]
    assert pc["topic"] == "overseas_transfers"


async def test_detail_already_given_is_not_asked_again(kb):
    pc = await run_prompt_check(Q["red"], {"payee_type": "New"})
    assert pc["missing_details"] == []
    assert "new payee" in pc["search_query"]


async def test_only_asks_when_needed(kb):
    pc = await run_prompt_check(Q["amber"], {})
    assert pc["missing_details"] == []
    assert len(pc["parts"]) == 2


async def test_wrong_assumption_gets_correction_note(kb):
    pc = await run_prompt_check(Q["assumption"], {})
    assert pc["assumptions"] == ["The limit is S$10,000 for a new payee."]
    assert pc["known_details"] == {"payee_type": "New"}  # stated in the question, so not asked
    assert pc["missing_details"] == []
    assert pc["assumption_checks"][0]["label"] == "Contradicted"
    note = pc["correction_notes"][0]
    assert note.startswith("Note:") and "S$5,000" in note and "not S$10,000" in note
    assert pc["parts"] == ["Can I send S$8,000 to a new payee?"]


async def test_correct_assumption_has_no_note(kb):
    pc = await run_prompt_check("Since the limit is S$5,000, can I send S$3,000 to a new payee?", {})
    assert pc["assumption_checks"][0]["label"] == "Supported"
    assert pc["correction_notes"] == []


async def test_search_query_never_replaces_question(kb):
    pc = await run_prompt_check(Q["green"], {})
    assert pc["search_query"] and pc["search_query"] != Q["green"]
    assert pc["parts"] == [Q["green"]]


async def test_max_followups_respected(kb):
    from app.core.runtime import update_runtime

    update_runtime({"max_followups": 0})
    try:
        assert (await run_prompt_check(Q["red"], {}))["missing_details"] == []
    finally:
        update_runtime({"max_followups": 2})
