"""Step 5b - self-correction: Amber only, at most ONE retry, original kept."""
import pytest

from app.models import ReviewItem, Run
from app.services import ocbc_ai, workflow
from app.services.demo import SCENARIOS
from app.services.self_correction import build_feedback, what_changed

Q = {s["id"]: s["question"] for s in SCENARIOS}
AMBER_ANSWER = ("Transfers usually arrive within 1 business day. There is no fee for transfers below S$1,000. "
                "(Payments Procedure v2026, §5)")


async def run_scenario(db, question, details=None):
    run = await workflow.start_run(db, question, details)
    await workflow.process_run(run.id)
    db.expire_all()
    return db.get(Run, run.id)


async def test_amber_fixed_by_one_retry(db):
    run = await run_scenario(db, Q["amber"])
    assert run.original_verdict == "Amber" and run.retried
    assert run.retry_verdict == "Green" and run.routed_to == "employee"
    assert run.original_answer == AMBER_ANSWER  # the original is never overwritten
    assert run.final_answer == run.retry_answer != run.original_answer
    assert "Transfers usually arrive within 1 business day" in run.retry_feedback


async def test_no_evidence_retry_fails_and_goes_to_review(db):
    run = await run_scenario(db, Q["no_evidence"])
    assert run.original_verdict == "Amber" and run.retry_verdict == "Amber"
    assert run.routed_to == "review"
    assert "No approved source was found" in run.retry_answer
    item = db.query(ReviewItem).filter(ReviewItem.run_id == run.id).one()
    assert item.queue_reason == "amber_after_retry"


async def test_green_and_red_are_never_retried(db):
    green = await run_scenario(db, Q["green"])
    red = await run_scenario(db, Q["red"], {"payee_type": "New"})
    assert not green.retried and not red.retried
    assert green.retry_answer is None and red.retry_answer is None


async def test_retry_limit_is_one_even_if_still_amber(db, monkeypatch):
    """OCBC AI keeps giving the same Amber answer: it is asked again exactly once."""
    calls = []

    async def always_amber(*args, **kwargs):
        calls.append(kwargs.get("feedback", ""))
        return AMBER_ANSWER, []

    monkeypatch.setattr(ocbc_ai, "generate_answer", always_amber)
    run = await run_scenario(db, Q["amber"])
    assert len(calls) == 2  # the first answer + one retry
    assert calls[0] == "" and calls[1]
    assert run.retry_verdict == "Amber" and run.routed_to == "review"


async def test_retry_that_turns_red_goes_to_review(db, monkeypatch):
    answers = iter([AMBER_ANSWER, "The daily overseas transfer limit is S$10,000. (Payments Procedure v2024, §3.1)"])

    async def scripted(*args, **kwargs):
        return next(answers), []

    monkeypatch.setattr(ocbc_ai, "generate_answer", scripted)
    run = await run_scenario(db, Q["amber"])
    assert run.retry_verdict == "Red" and run.routed_to == "review"


def test_feedback_names_the_claim_and_gives_correct_passages():
    checks = {
        "sentences": [
            {"index": 0, "text": "X is true.", "label": "Unsupported", "evidence": []},
            {"index": 1, "text": "Y is free.", "label": "Supported", "evidence": [
                {"doc_id": "d", "doc_label": "Doc v1", "section": "5", "section_label": "§5", "text": "Y is free."}]},
        ],
        "flags": [
            {"type": "unsupported", "sentence_index": 0, "message": "m"},
            {"type": "conflict_note", "sentence_index": None, "message": "info only"},
        ],
    }
    text, flagged, passages = build_feedback(checks)
    assert "The claim 'X is true.' has no supporting passage" in text
    assert "(Doc v1, §5) Y is free." in text
    assert "info only" not in text
    assert flagged == ["X is true."] and len(passages) == 1


def test_what_changed_diff():
    diff = what_changed(AMBER_ANSWER, "Arrival time is not stated. There is no fee for transfers below S$1,000. "
                                      "(Payments Procedure v2026, §5)")
    assert [d["type"] for d in diff] == ["removed", "added", "same"]


@pytest.mark.parametrize("scenario", ["amber"])
def test_api_returns_what_changed(client, scenario):
    run = client.post("/api/chat/ask", json={"question": Q[scenario]}).json()
    run = client.get(f"/api/chat/runs/{run['id']}").json()
    assert run["retried"] and run["final_verdict"] == "Green"
    assert {d["type"] for d in run["what_changed"]} == {"removed", "added", "same"}
