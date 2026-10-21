"""Chat API: ask -> follow-up chip -> OCBC AI answer (background task)."""
from app.services.demo import SCENARIOS

Q = {s["id"]: s["question"] for s in SCENARIOS}


def test_scenarios_listed(client):
    assert [s["id"] for s in client.get("/api/chat/scenarios").json()] == [
        "red", "amber", "green", "assumption", "no_evidence",
    ]


def test_ask_with_followup_then_answer(client):
    run = client.post("/api/chat/ask", json={"question": Q["red"]}).json()
    assert run["status"] == "needs_details"
    assert run["original_answer"] is None  # OCBC AI waits for the detail

    run = client.post(f"/api/chat/runs/{run['id']}/details", json={"details": {"payee_type": "New"}}).json()
    assert run["details"]["payee_type"] == "New"

    run = client.get(f"/api/chat/runs/{run['id']}").json()  # background task has finished
    assert run["status"] == "done"
    assert "(Payments Procedure v2024, §3.1)" in run["original_answer"]


def test_details_rejected_when_not_waiting(client):
    run = client.post("/api/chat/ask", json={"question": Q["green"]}).json()
    assert client.post(f"/api/chat/runs/{run['id']}/details", json={"details": {"x": "y"}}).status_code == 409


def test_correction_note_returned_before_answer(client):
    run = client.post("/api/chat/ask", json={"question": Q["assumption"]}).json()
    assert run["prompt_check"]["correction_notes"]
    assert client.get(f"/api/chat/runs/{run['id']}").json()["status"] == "done"


def test_unknown_run_is_404(client):
    assert client.get("/api/chat/runs/999999").status_code == 404


def test_events_logged(client, db):
    from app.models import EventLog

    run = client.post("/api/chat/ask", json={"question": Q["green"]}).json()
    events = [e.event for e in db.query(EventLog).filter(EventLog.run_id == run["id"]).order_by(EventLog.id)]
    assert events == ["question_asked", "prompt_checked", "ocbc_answered", "run_finished"]
