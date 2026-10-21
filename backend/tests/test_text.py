"""Text helpers: sentences, citations, figures."""
from app.services.text import extract_figures, parse_citations, split_sentences


def test_citation_after_full_stop_belongs_to_previous_sentence():
    s = split_sentences(
        "The daily overseas transfer limit is S$10,000. Verify the customer's ID and process the transfer. "
        "(Payments Procedure v2024, §3.1)"
    )
    assert [x.text for x in s] == [
        "The daily overseas transfer limit is S$10,000.",
        "Verify the customer's ID and process the transfer.",
    ]
    assert s[0].citations == [] and s[1].citations[0].sections == ["3.1"]


def test_multiple_sections_and_documents():
    cites = parse_citations("x (Payments Procedure v2026, §3.1, §4.2; Branch FAQ 2023, §2)")
    assert [(c.doc_label, c.sections) for c in cites] == [
        ("Payments Procedure v2026", ["3.1", "4.2"]),
        ("Branch FAQ 2023", ["2"]),
    ]


def test_abbreviation_does_not_split_sentence():
    assert len(split_sentences("Interest of 0.05% p.a. is paid on the amount. It is small.")) == 2


def test_figures():
    figs = extract_figures("S$10,000 per day, 0.05% p.a., within 3 months, from 2026-03-01 and S$ 1,000.")
    assert figs == [("money", "s$10,000"), ("money", "s$1,000"), ("percent", "0.05%"), ("date", "2026-03-01"), ("number", "3")]
