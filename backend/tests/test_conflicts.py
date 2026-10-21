"""Conflict detection: same topic, same field, different value - computed once at load."""
from app.services.ingest import KBDocument, compute_conflicts


def make_doc(id, topic="t", fields=None, status="current", superseded_by=None, date="2025-01-01"):
    return KBDocument(
        id=id, title=id, topic=topic, version="v1", effective_date=date, status=status,
        superseded_by=superseded_by, owner="", required_details=[], fields=fields or {}, path="",
    )


def test_planted_conflict_found_in_real_kb(kb):
    assert len(kb.conflicts) == 1
    c = kb.conflicts[0]
    assert (c.doc_a, c.doc_b) == ("payments-procedure-v2026", "branch-faq-2023")  # newer first
    assert c.field == "overseas_limit_new_payee"
    assert (c.value_a, c.value_b) == ("S$5,000", "S$10,000")


def test_same_topic_same_field_different_value_is_conflict():
    pairs = compute_conflicts([make_doc("a", fields={"limit": "S$5,000"}), make_doc("b", fields={"limit": "S$10,000"})])
    assert len(pairs) == 1


def test_same_value_is_not_conflict():
    assert compute_conflicts([make_doc("a", fields={"limit": "S$5,000"}), make_doc("b", fields={"limit": "s$5,000 "})]) == []


def test_different_topic_is_not_conflict():
    docs = [make_doc("a", topic="x", fields={"limit": "1"}), make_doc("b", topic="y", fields={"limit": "2"})]
    assert compute_conflicts(docs) == []


def test_superseded_versions_are_not_conflicts():
    old = make_doc("old", fields={"limit": "1"}, status="superseded", superseded_by="new")
    new = make_doc("new", fields={"limit": "2"})
    assert compute_conflicts([old, new]) == []


def test_version_chain_even_if_both_marked_current():
    old = make_doc("old", fields={"limit": "1"}, superseded_by="new")
    new = make_doc("new", fields={"limit": "2"})
    assert compute_conflicts([old, new]) == []


def test_newer_document_listed_first():
    pairs = compute_conflicts([
        make_doc("a", fields={"f": "1"}, date="2020-01-01"),
        make_doc("b", fields={"f": "2"}, date="2026-01-01"),
    ])
    assert pairs[0].doc_a == "b"
