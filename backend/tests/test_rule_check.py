"""Check A - one test group per rule (plain Python, no LLM)."""
from app.services.checks.rule_check import run_rule_check


def types(result):
    return [f["type"] for f in result["flags"]]


# --- citation_exists ---------------------------------------------------------
def test_citation_exists_passes(kb):
    r = run_rule_check("No fee for overseas transfers below S$1,000. (Payments Procedure v2026, §5)")
    assert r["rules"]["citation_exists"]["passed"]
    assert types(r) == []


def test_no_citation_fails(kb):
    r = run_rule_check("Transfers are free.")
    assert not r["rules"]["citation_exists"]["passed"]
    assert "no_citation" in types(r)


def test_citation_to_missing_section_fails(kb):
    r = run_rule_check("Transfers are free. (Payments Procedure v2026, §9.9)")
    assert not r["rules"]["citation_exists"]["passed"]
    assert "citation_not_found" in types(r)


def test_citation_to_unknown_document_fails(kb):
    r = run_rule_check("Transfers are free. (Imaginary Manual v2030, §1)")
    assert "citation_not_found" in types(r) and "no_citation" in types(r)


# --- source_current ------------------------------------------------------------
def test_superseded_source_is_critical(kb):
    r = run_rule_check("The limit is S$10,000. (Payments Procedure v2024, §3.1)")
    assert not r["rules"]["source_current"]["passed"]
    flag = next(f for f in r["flags"] if f["type"] == "outdated_source")
    assert flag["severity"] == "critical"
    assert "Payments Procedure v2026" in flag["message"]


def test_current_source_passes(kb):
    assert run_rule_check("The limit is S$5,000. (Payments Procedure v2026, §3.1)")["rules"]["source_current"]["passed"]


# --- figures_match ---------------------------------------------------------------
def test_figure_in_cited_passage_passes(kb):
    r = run_rule_check("New payees: S$5,000 per day. (Payments Procedure v2026, §3.1)")
    assert r["rules"]["figures_match"]["passed"]


def test_figure_not_in_cited_passage_fails(kb):
    r = run_rule_check("New payees: S$7,500 per day. (Payments Procedure v2026, §3.1)")
    assert not r["rules"]["figures_match"]["passed"]
    assert "figure_mismatch" in types(r)


def test_uncited_sentence_is_covered_by_next_citation(kb):
    r = run_rule_check("Transfers arrive within 1 business day. No fee below S$1,000. (Payments Procedure v2026, §5)")
    assert r["rules"]["figures_match"]["detail"] == [0]  # "1" is not in §5
    assert r["sentences"][0]["citations"][0]["label"] == "Payments Procedure v2026"


def test_figures_from_the_question_are_ignored(kb):
    r = run_rule_check("New payees are limited to S$5,000, so S$8,000 is too much. (Payments Procedure v2026, §3.1)",
                       ignore_figures={"s$8,000"})
    assert r["rules"]["figures_match"]["passed"]


def test_percentages_and_dates(kb):
    ok = run_rule_check("Interest of 0.05% p.a. is paid. (Fixed Deposit Early Withdrawal Procedure v2025, §2)")
    bad = run_rule_check("Interest of 0.5% p.a. is paid. (Fixed Deposit Early Withdrawal Procedure v2025, §2)")
    assert ok["rules"]["figures_match"]["passed"] and not bad["rules"]["figures_match"]["passed"]
    dated = run_rule_check("This applies from 2026-03-01. (Payments Procedure v2026, §1)")
    assert not dated["rules"]["figures_match"]["passed"]


# --- quotes_match ------------------------------------------------------------------
def test_exact_quote_passes(kb):
    r = run_rule_check('The procedure says "A scam-risk check is required". (Payments Procedure v2026, §4.2)')
    assert r["rules"]["quotes_match"]["passed"]


def test_quote_with_different_wording_is_critical(kb):
    r = run_rule_check('The procedure says "A scam check is optional". (Payments Procedure v2026, §4.2)')
    assert not r["rules"]["quotes_match"]["passed"]
    assert next(f for f in r["flags"] if f["type"] == "quote_mismatch")["severity"] == "critical"


def test_curly_quotes_supported(kb):
    r = run_rule_check("It says “verify the customer's ID”. (Payments Procedure v2026, §4.1)")
    assert r["rules"]["quotes_match"]["passed"]
