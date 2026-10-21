"""Step 5 - verdict rules (no average score) and routing."""
import pytest

from app.services.verdict import CRITICAL_TYPES, SEVERITY, decide, make_flag, route


def flag(type_):
    check = "C" if type_.startswith("part_") else "A" if type_ in {
        "outdated_source", "quote_mismatch", "no_citation", "citation_not_found", "figure_mismatch"} else "B"
    return make_flag(check, type_, "test")


def test_critical_types_are_the_four_from_the_brief():
    assert CRITICAL_TYPES == {"contradicted", "outdated_source", "missing_exception", "quote_mismatch"}


def test_no_flags_is_green():
    assert decide([]) == "Green"


def test_info_notes_stay_green():
    assert decide([flag("conflict_note")]) == "Green"


@pytest.mark.parametrize("t", [t for t, s in SEVERITY.items() if s == "warning"])
def test_each_warning_alone_is_amber(t):
    assert decide([flag(t)]) == "Amber"


@pytest.mark.parametrize("t", sorted(CRITICAL_TYPES))
def test_critical_flag_always_red(t):
    # alone, and mixed with any number of warnings / info notes
    assert decide([flag(t)]) == "Red"
    others = [flag(x) for x, s in SEVERITY.items() if s != "critical"]
    assert decide(others + [flag(t)]) == "Red"
    assert decide([flag(t)] + others) == "Red"


def test_routing():
    assert route("Green", retried=False) == "employee"
    assert route("Amber", retried=False) == "retry"
    assert route("Red", retried=False) == "review"


def test_retry_limit_is_one():
    # After one retry, an Amber answer is never retried again
    assert route("Amber", retried=True) == "review"
    assert route("Red", retried=True) == "review"
    assert route("Green", retried=True) == "employee"
