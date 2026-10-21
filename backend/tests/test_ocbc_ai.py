"""Step 3 - simulated OCBC AI: answers depend on what its retriever returns."""
from app.services.demo import SCENARIOS
from app.services.ocbc_ai import generate_answer
from app.services.text import parse_citations

Q = {s["id"]: s["question"] for s in SCENARIOS}
PARTS = ["What's the daily overseas transfer limit?", "What do I need to check before processing?"]


async def test_mr_tan_cites_superseded_procedure(db):
    answer, ctx = await generate_answer(db, Q["red"], {"payee_type": "New"}, "daily overseas transfer limit", PARTS)
    assert answer == (
        "The daily overseas transfer limit is S$10,000. Verify the customer's ID and process the transfer. "
        "(Payments Procedure v2024, §3.1)"
    )
    assert any(c["doc_id"] == "payments-procedure-v2024" for c in ctx)


async def test_after_retiring_v2024_answer_uses_current_procedure(db, retire_v2024):
    answer, ctx = await generate_answer(db, Q["red"], {"payee_type": "New"}, "daily overseas transfer limit", PARTS)
    assert all(c["doc_id"] != "payments-procedure-v2024" for c in ctx)
    assert "S$5,000" in answer and "scam-risk check" in answer
    assert parse_citations(answer)[0].doc_label == "Payments Procedure v2026"


async def test_amber_answer_has_unsupported_arrival_time(db):
    answer, _ = await generate_answer(db, Q["amber"], {}, "long overseas transfer take fee", [])
    assert answer.startswith("Transfers usually arrive within 1 business day.")


async def test_green_generic_answer_quotes_right_passage(db):
    answer, _ = await generate_answer(db, Q["green"], {}, "documents customer change mailing address", [Q["green"]])
    assert answer == (
        "The customer must provide photo ID and a proof of address dated within the last 3 months. "
        "(Address Change Procedure v2024, §2)"
    )


async def test_crypto_answer_has_no_citation(db):
    answer, _ = await generate_answer(db, Q["no_evidence"], {}, "process cryptocurrency transfer", [])
    assert parse_citations(answer) == []
