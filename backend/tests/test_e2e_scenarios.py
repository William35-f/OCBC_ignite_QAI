"""End-to-end: the five demo scenarios through the API, mock provider, as in the brief."""
import pytest

from app.models import Document
from app.services.demo import SCENARIOS

Q = {s["id"]: s["question"] for s in SCENARIOS}
DANIEL = ("For a new overseas payee, the limit is S$5,000 per day. Verify the customer's ID and complete the "
          "scam-risk check before processing.")


@pytest.fixture
def fresh_retriever(db):
    """Every scenario starts with v2024 still in OCBC AI's retriever (the planted bug)."""
    def enable():
        db.expire_all()  # the API may have changed the row in another session
        db.get(Document, "payments-procedure-v2024").retriever_enabled = True
        db.commit()

    enable()
    yield
    enable()


def ask(client, question, details=None):
    run = client.post("/api/chat/ask", json={"question": question, **({"details": details} if details else {})}).json()
    return client.get(f"/api/chat/runs/{run['id']}").json() if run["status"] != "needs_details" else run


def flags(checks):
    return {f["type"] for f in checks["flags"]}


def test_1_red_mr_tan(client, fresh_retriever):
    # Step 2 splits the question in 2 parts and asks about the payee
    run = ask(client, Q["red"])
    pc = run["prompt_check"]
    assert run["status"] == "needs_details" and len(pc["parts"]) == 2
    assert pc["missing_details"][0]["question"] == "Is this payee new or existing?"
    assert pc["missing_details"][0]["options"] == ["New", "Existing"]

    # Rachel picks New -> OCBC AI answers from the superseded procedure
    client.post(f"/api/chat/runs/{run['id']}/details", json={"details": {"payee_type": "New"}})
    run = client.get(f"/api/chat/runs/{run['id']}").json()
    assert run["original_answer"] == (
        "The daily overseas transfer limit is S$10,000. Verify the customer's ID and process the transfer. "
        "(Payments Procedure v2024, §3.1)")
    c = run["original_checks"]
    assert not c["rule"]["source_current"]["passed"]                       # 4A superseded
    assert c["sentences"][0]["label"] == "Contradicted"                     # 4B S$10,000
    assert c["sentences"][0]["evidence"][0]["section"] == "3.1"
    assert any(e["id"] == "payments-procedure-v2026:C1" and e["applies"] and not e["mentioned"]
               for e in c["source"]["exceptions"])                          # 4B scam-risk check missing
    assert [p["status"] for p in c["intent"]] == ["answered", "partly"]     # 4C part 2 incomplete
    assert run["final_verdict"] == "Red" and run["routed_to"] == "review" and not run["retried"]

    # Daniel corrects it -> golden set
    item = next(i for i in client.get("/api/review/queue").json() if i["run_id"] == run["id"])
    client.post(f"/api/review/items/{item['id']}/decide", json={
        "action": "correct", "reason": "Outdated source, missing exception", "corrected_answer": DANIEL})
    assert any(g["correct_answer"] == DANIEL for g in client.get("/api/review/golden").json())

    # Priya: retire v2024 -> retest passes -> the same question is Green
    sugg = client.get("/api/admin/suggestions").json()
    assert any(s["title"] == "Retire Payments Procedure v2024 from OCBC AI's retriever" and s["can_apply"]
               for s in sugg)
    client.post("/api/admin/fixes/retire", json={"doc_id": "payments-procedure-v2024"})
    assert client.post("/api/admin/retest").json()["passed"]
    again = ask(client, Q["red"], {"payee_type": "New"})
    assert again["final_verdict"] == "Green"


def test_2_amber_fixed_by_one_retry(client, fresh_retriever):
    run = ask(client, Q["amber"])
    assert run["original_answer"].startswith("Transfers usually arrive within 1 business day.")
    labels = [s["label"] for s in run["original_checks"]["sentences"]]
    assert labels == ["Unsupported", "Supported"]
    assert run["original_verdict"] == "Amber" and run["retried"]
    assert run["retry_answer"].startswith("Arrival time depends on the receiving bank")
    assert run["final_verdict"] == "Green" and run["routed_to"] == "employee"
    assert {d["type"] for d in run["what_changed"]} == {"removed", "added", "same"}


def test_3_green(client, fresh_retriever):
    run = ask(client, Q["green"])
    assert run["final_verdict"] == "Green" and run["routed_to"] == "employee" and not run["retried"]
    assert all(s["label"] == "Supported" for s in run["original_checks"]["sentences"])


def test_4_wrong_assumption_corrected_before_answering(client, fresh_retriever):
    run = ask(client, Q["assumption"])
    note = run["prompt_check"]["correction_notes"][0]
    assert "S$5,000" in note and "not S$10,000" in note
    assert run["prompt_check"]["missing_details"] == []  # "new payee" is already in the question
    assert run["question"] == Q["assumption"]  # never silently replaced
    assert run["final_verdict"] == "Red"


def test_5_no_evidence(client, fresh_retriever):
    run = ask(client, Q["no_evidence"])
    assert run["prompt_check"]["missing_details"] == []
    assert [s["label"] for s in run["original_checks"]["sentences"]] == ["Unable to verify"]
    assert run["original_verdict"] == "Amber" and run["retried"]
    assert "No approved source was found" in run["retry_answer"]
    assert run["retry_verdict"] == "Amber" and run["routed_to"] == "review"
