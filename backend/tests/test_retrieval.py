"""Retrieval scopes: OCBC AI sees everything, Q AI sees current documents only."""
MR_TAN = "What's the daily overseas transfer limit, and what do I need to check before processing?"


def test_ocbc_scope_includes_superseded(kb):
    hits = kb.search(MR_TAN, k=5)  # no filter = OCBC AI's default view (all documents)
    assert "payments-procedure-v2024" in {h.passage.doc_id for h in hits}


def test_current_scope_excludes_superseded(kb):
    for h in kb.search_current(MR_TAN, k=10):
        assert kb.doc(h.passage.doc_id).status == "current"


def test_retired_document_not_returned(kb):
    enabled = [d for d in kb.docs if d != "payments-procedure-v2024"]
    assert all(h.passage.doc_id != "payments-procedure-v2024" for h in kb.search(MR_TAN, 10, enabled))


def test_lookups(kb):
    assert kb.doc_by_label("payments procedure V2026").id == "payments-procedure-v2026"
    assert "S$5,000" in kb.passage("payments-procedure-v2026", "§3.1").text
    assert "scam-risk" in kb.passage("payments-procedure-v2026", "4").text  # §4 = §4.1 + §4.2
    assert kb.passage("payments-procedure-v2026", "9") is None
