"""Step 7 - human review queue, decisions and the golden set."""
from app.services.demo import SCENARIOS

Q = {s["id"]: s["question"] for s in SCENARIOS}
DANIEL = ("For a new overseas payee, the limit is S$5,000 per day. Verify the customer's ID and complete the "
          "scam-risk check before processing.")


def red_run(client):
    run = client.post("/api/chat/ask", json={"question": Q["red"]}).json()
    client.post(f"/api/chat/runs/{run['id']}/details", json={"details": {"payee_type": "New"}})
    return run["id"]


def item_for(client, run_id):
    return next(i for i in client.get("/api/review/queue").json() if i["run_id"] == run_id)


def test_queue_holds_red_amber_after_retry_and_reported(client):
    red_id = red_run(client)
    amber = client.post("/api/chat/ask", json={"question": Q["no_evidence"]}).json()
    green = client.post("/api/chat/ask", json={"question": Q["green"]}).json()
    client.post(f"/api/chat/runs/{green['id']}/report", json={"reason": "Not sure"})
    reasons = {i["run_id"]: i["queue_reason"] for i in client.get("/api/review/queue").json()}
    assert reasons[red_id] == "red"
    assert reasons[amber["id"]] == "amber_after_retry"
    assert reasons[green["id"]] == "reported"


def test_detail_has_question_answers_flags_and_evidence(client):
    item = item_for(client, red_run(client))
    detail = client.get(f"/api/review/items/{item['id']}").json()
    run = detail["run"]
    assert run["question"] == Q["red"] and run["original_answer"]
    assert {f["type"] for f in run["original_checks"]["flags"]} >= {"outdated_source", "contradicted"}
    assert run["original_checks"]["sentences"][0]["evidence"]


def test_reason_is_required(client):
    item = item_for(client, red_run(client))
    r = client.post(f"/api/review/items/{item['id']}/decide", json={"action": "reject", "reason": ""})
    assert r.status_code == 400


def test_correct_needs_new_text(client):
    item = item_for(client, red_run(client))
    r = client.post(f"/api/review/items/{item['id']}/decide",
                    json={"action": "correct", "reason": "Outdated source", "corrected_answer": ""})
    assert r.status_code == 400


def test_daniel_corrects_mr_tan_and_it_joins_golden_set(client):
    item = item_for(client, red_run(client))
    out = client.post(f"/api/review/items/{item['id']}/decide", json={
        "action": "correct", "reason": "Outdated source, missing exception", "corrected_answer": DANIEL,
    }).json()
    assert out["item"]["status"] == "corrected" and out["item"]["reviewer"] == "Daniel Ng"
    assert out["run"]["review"]["corrected_answer"] == DANIEL
    golden = client.get("/api/review/golden").json()[0]
    assert golden["correct_answer"] == DANIEL
    assert golden["details"] == {"payee_type": "New"}
    assert golden["source_docs"] == ["Payments Procedure v2026"]
    # cannot decide twice
    again = client.post(f"/api/review/items/{item['id']}/decide", json={"action": "reject", "reason": "x x x"})
    assert again.status_code == 400


def test_approve_adds_final_answer_to_golden_set(client):
    green = client.post("/api/chat/ask", json={"question": Q["green"]}).json()
    client.post(f"/api/chat/runs/{green['id']}/report", json={"reason": ""})
    item = item_for(client, green["id"])
    client.post(f"/api/review/items/{item['id']}/decide", json={"action": "approve", "reason": "Answer is right"})
    golden = client.get("/api/review/golden").json()[0]
    assert golden["source_docs"] == ["Address Change Procedure v2024"]


def test_reject_does_not_add_to_golden_set(client):
    before = len(client.get("/api/review/golden").json())
    item = item_for(client, red_run(client))
    client.post(f"/api/review/items/{item['id']}/decide", json={"action": "reject", "reason": "Wrong limit"})
    assert len(client.get("/api/review/golden").json()) == before
    assert client.get(f"/api/review/items/{item['id']}").json()["item"]["status"] == "rejected"
