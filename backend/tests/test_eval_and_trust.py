"""Feature 08 - the eval set and the Trust Challenge."""
from collections import Counter

from app.eval import evaluate_case, load_cases, run_eval


def test_eval_set_has_ten_cases_per_type():
    cases = load_cases()
    assert len(cases) == 40
    assert Counter(c["type"] for c in cases) == {
        "correct": 10, "missing_exception": 10, "outdated_source": 10, "no_evidence": 10}
    for c in cases:
        assert c["question"] and c["answer"] and c["expected_verdict"] in ("Green", "Amber", "Red")


async def test_one_case_scored_per_check(kb):
    case = next(c for c in load_cases() if c["id"] == "O01")
    row = await evaluate_case(case)
    assert row["got_verdict"] == "Red" and row["verdict_ok"]
    assert row["per_check"] == {"A": True, "B": True, "C": True}


async def test_eval_metrics_regression_guard(kb):
    """Not a target to tune to - a guard so the checks do not silently get worse."""
    results = await run_eval(save=False)
    assert results["missed_errors"]["count"] == 0
    assert results["false_flags"]["count"] <= 1
    assert results["verdict_accuracy"] >= 0.9
    assert set(results["per_check_accuracy"]) == {"A", "B", "C"}
    assert results["retry"]["amber_first"] >= 2 and results["retry"]["fixed"] >= 1


def test_trust_items_hide_ground_truth(client):
    items = client.get("/api/trust/items").json()
    assert len(items) == 10
    assert all("trustworthy" not in i and "why" not in i for i in items)
    assert all(i["checks"]["verdict"] in ("Green", "Amber", "Red") for i in items)


def test_trust_answers_scored_per_round(client):
    sid = "test-session-1"
    client.post("/api/trust/answers", json={"session_id": sid, "round": "A", "item_id": "C01", "choice": "dont_trust"})
    client.post("/api/trust/answers", json={"session_id": sid, "round": "B", "item_id": "C01", "choice": "trust"})
    client.post("/api/trust/answers", json={"session_id": sid, "round": "B", "item_id": "M03", "choice": "dont_trust"})
    score = client.get(f"/api/trust/score/{sid}").json()["score"]
    assert score["A"] == {"answers": 1, "correct": 0, "accuracy": 0.0}
    assert score["B"] == {"answers": 2, "correct": 2, "accuracy": 1.0}
    summary = client.get("/api/trust/summary").json()
    assert summary["participants"] >= 1


def test_trust_bad_answer_rejected(client):
    r = client.post("/api/trust/answers", json={"session_id": "xxxx", "round": "C", "item_id": "C01", "choice": "trust"})
    assert r.status_code == 400
