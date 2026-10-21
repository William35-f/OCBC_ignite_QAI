"""Knowledge-base parsing: metadata, numbered sections, conditions."""
from app.core.config import settings
from app.services.ingest import parse_document


def _v2026():
    return parse_document(settings.kb_dir / "payments-procedure-v2026.md")


def test_front_matter_and_label():
    doc = _v2026()
    assert doc.label == "Payments Procedure v2026"
    assert doc.status == "current"
    assert doc.required_details[0]["name"] == "payee_type"
    assert doc.required_details[0]["options"] == ["New", "Existing"]


def test_numbered_sections_are_passages():
    doc = _v2026()
    sections = {p.section: p.text for p in doc.passages if p.kind == "section"}
    assert sections["3.1"] == "Overseas transfer limit: S$10,000 per day for existing payees; S$5,000 per day for new payees."
    assert "scam-risk check" in sections["4.2"]
    assert "3" not in sections  # "## §3 Limits" is only a parent heading


def test_no_arrival_time_anywhere(kb):
    # The Amber demo depends on no document stating an arrival time
    for doc in kb.docs.values():
        for p in doc.passages:
            assert "business day" not in p.text.lower()


def test_conditions_parsed_with_key_phrase():
    c1 = _v2026().conditions[0]
    assert c1.id == "C1"
    assert c1.key_phrase == "scam-risk check"
    assert c1.section_ref == "4.2"
    assert "**" not in c1.text


def test_condition_applies():
    c1, c2, _ = _v2026().conditions
    assert c1.applies("What do I check?", {"payee_type": "New"})
    assert not c1.applies("What do I check?", {"payee_type": "Existing"})
    assert not c1.applies("How much is the fee?", {})
    assert c2.applies("Can I send money to a sanctioned country?", {})


def test_every_document_has_conditions(kb):
    for doc in kb.docs.values():
        assert doc.conditions, f"{doc.id} has no Conditions and exceptions"
