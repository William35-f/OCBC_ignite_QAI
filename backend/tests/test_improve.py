"""Step 8 - dashboard, template fix suggestions, Apply fix, Run retest.

The main story: Mr Tan's answer is Red because OCBC AI still retrieves the
superseded Payments Procedure v2024. Daniel corrects it (golden set). The
retest fails until Priya retires v2024, then passes and the fix is done.
"""
from app.models import Document
from app.services.demo import SCENARIOS

Q = {s["id"]: s["question"] for s in SCENARIOS}
DANIEL = ("For a new overseas payee, the limit is S$5,000 per day. Verify the customer's ID and complete the "
          "scam-risk check before processing.")


def test_mr_tan_story_red_to_green(client, db):
    # Rachel: Red
    run = client.post("/api/chat/ask", json={"question": Q["red"]}).json()
    client.post(f"/api/chat/runs/{run['id']}/details", json={"details": {"payee_type": "New"}})
    assert client.get(f"/api/chat/runs/{run['id']}").json()["final_verdict"] == "Red"

    # Daniel: correct it -> golden set
    item = next(i for i in client.get("/api/review/queue").json() if i["run_id"] == run["id"])
    client.post(f"/api/review/items/{item['id']}/decide", json={
        "action": "correct", "reason": "Outdated source, missing exception", "corrected_answer": DANIEL})

    # Priya: the template suggestion is there
    sugg = client.get("/api/admin/suggestions").json()
    retire = next(s for s in sugg if s["id"] == "retire:payments-procedure-v2024")
    assert retire["title"] == "Retire Payments Procedure v2024 from OCBC AI's retriever"
    assert "Payments Procedure v2024 is still being retrieved" in retire["evidence"]
    assert retire["can_apply"] and retire["status"] == "open"
    titles = [s["title"] for s in sugg]
    assert "Resolve conflict between Payments Procedure v2026 and Branch FAQ 2023" in titles

    # Retest before the fix fails on the golden answer
    before = client.post("/api/admin/retest").json()
    assert not before["passed"]
    golden = [r for r in before["results"] if r["kind"] == "golden" and r["question"] == Q["red"]]
    assert golden and not golden[-1]["passed"] and golden[-1]["got"] == "Red"

    # Apply fix -> applied, not yet done
    client.post("/api/admin/fixes/retire", json={"doc_id": "payments-procedure-v2024"})
    s = next(x for x in client.get("/api/admin/suggestions").json() if x["id"] == "retire:payments-procedure-v2024")
    assert s["status"] == "applied" and not s["can_apply"]

    # Retest after the fix passes, and the fix counts as done
    after = client.post("/api/admin/retest").json()
    assert after["passed"], [r for r in after["results"] if not r["passed"]]
    s = next(x for x in client.get("/api/admin/suggestions").json() if x["id"] == "retire:payments-procedure-v2024")
    assert s["status"] == "done"

    # Mr Tan's question now goes Green for Rachel
    run = client.post("/api/chat/ask", json={"question": Q["red"], "details": {"payee_type": "New"}}).json()
    run = client.get(f"/api/chat/runs/{run['id']}").json()
    assert run["final_verdict"] == "Green" and "S$5,000" in run["final_answer"]

    # put the retriever back for other tests
    db.expire_all()  # the API changed the row in another session
    db.get(Document, "payments-procedure-v2024").retriever_enabled = True
    db.commit()


def test_coverage_suggestion_for_unverifiable_topic(client):
    client.post("/api/chat/ask", json={"question": Q["no_evidence"]})
    titles = [s["title"] for s in client.get("/api/admin/suggestions").json()]
    assert any(t.startswith("Add coverage for") and "crypto" in t for t in titles)


def test_dashboard_numbers(client):
    client.post("/api/chat/ask", json={"question": Q["green"]})
    d = client.get("/api/admin/dashboard").json()
    assert d["totals"]["answers"] >= 1 and d["totals"]["green"] >= 1
    assert d["verdicts_over_time"] and set(d["verdicts_over_time"][0]) == {"day", "Green", "Amber", "Red"}
    assert {"approved", "corrected", "rejected"} == set(d["reviewer_decisions"])


def test_retest_runs_do_not_enter_review_queue_or_dashboard(client):
    before_queue = len(client.get("/api/review/queue?status=all").json())
    before_answers = client.get("/api/admin/dashboard").json()["totals"]["answers"]
    client.post("/api/admin/retest")
    assert len(client.get("/api/review/queue?status=all").json()) == before_queue
    assert client.get("/api/admin/dashboard").json()["totals"]["answers"] == before_answers


def test_errors_are_counted_against_the_cited_document(client):
    run = client.post("/api/chat/ask", json={"question": Q["red"], "details": {"payee_type": "New"}}).json()
    run = client.get(f"/api/chat/runs/{run['id']}").json()
    assert run["final_verdict"] == "Red", (run["original_answer"], [f["type"] for f in run["original_checks"]["flags"]])
    docs = {d["doc_id"]: d for d in client.get("/api/admin/dashboard").json()["doc_errors"]}
    assert docs["payments-procedure-v2024"]["errors"]["contradicted"] >= 1
    # v2026 is the evidence that caught the contradiction, not its cause
    assert "contradicted" not in docs.get("payments-procedure-v2026", {}).get("errors", {})


def test_activity_log(client):
    client.post("/api/chat/ask", json={"question": Q["green"]})
    events = {e["event"] for e in client.get("/api/admin/activity").json()}
    assert {"question_asked", "prompt_checked", "ocbc_answered", "answer_checked", "run_finished"} <= events


def test_unknown_document_cannot_be_retired(client):
    assert client.post("/api/admin/fixes/retire", json={"doc_id": "nope"}).status_code == 404
