"""API smoke tests for Phase 1 endpoints."""


def test_health(client):
    assert client.get("/api/health").json()["ok"] is True


def test_documents_listed_with_retriever_switch(client):
    docs = client.get("/api/kb/documents").json()
    assert len(docs) == 10
    v2024 = next(d for d in docs if d["id"] == "payments-procedure-v2024")
    assert v2024["status"] == "superseded" and v2024["retriever_enabled"] is True


def test_document_detail(client):
    doc = client.get("/api/kb/documents/payments-procedure-v2026").json()
    assert doc["label"] == "Payments Procedure v2026"
    assert any(p["section"] == "4.2" for p in doc["passages"])
    assert doc["conditions"][0]["key_phrase"] == "scam-risk check"


def test_conflicts_table(client):
    conflicts = client.get("/api/kb/conflicts").json()
    assert [(c["doc_a_label"], c["doc_b_label"]) for c in conflicts] == [("Payments Procedure v2026", "Branch FAQ 2023")]


def test_retriever_toggle_changes_ocbc_view(client):
    q = "daily overseas transfer limit"
    ocbc = lambda: {h["doc_id"] for h in client.get("/api/kb/search", params={"q": q, "scope": "ocbc", "k": 10}).json()}
    assert "payments-procedure-v2024" in ocbc()
    client.post("/api/kb/documents/payments-procedure-v2024/retriever", json={"enabled": False})
    assert "payments-procedure-v2024" not in ocbc()
    client.post("/api/kb/documents/payments-procedure-v2024/retriever", json={"enabled": True})


def test_settings_roundtrip(client):
    assert client.get("/api/settings").json()["llm_provider"] == "mock"
    out = client.put("/api/settings", json={"similarity_threshold": 0.5}).json()
    assert out["similarity_threshold"] == 0.5
    assert client.put("/api/settings", json={"llm_provider": "banana"}).status_code == 400
    client.put("/api/settings", json={"similarity_threshold": 0.40})
    assert client.post("/api/settings/test").json()["ok"] is True
