"""Step 5 - verdict and routing. Plain Python rules, no average score.

  Red   : any critical flag (a critical flag ALWAYS means Red)
  Amber : no critical flags, but at least one warning
  Green : no critical flags and no warnings (info notes are fine)

Routing:
  Green -> employee
  Amber -> one self-correction retry (Step 5b); after a retry -> review queue
  Red   -> review queue
"""
from app.schemas.workflow import Flag

# Every flag type and how serious it is. Critical types come from the brief:
# contradicted claim, outdated source, missing required exception, quote mismatch.
SEVERITY: dict[str, str] = {
    # Check A - rules and timeframes
    "outdated_source": "critical",
    "quote_mismatch": "critical",
    "no_citation": "warning",
    "citation_not_found": "warning",
    "figure_mismatch": "warning",
    # Check B - sources
    "contradicted": "critical",
    "missing_exception": "critical",
    "partly_supported": "warning",
    "unsupported": "warning",
    "unable_to_verify": "warning",
    "conflict_older_source": "warning",  # cites the older side of a known conflict
    "conflict_note": "info",  # cites the newer side: just a note
    # Check C - intent
    "part_partly_answered": "warning",
    "part_not_answered": "warning",
}
CRITICAL_TYPES = {t for t, s in SEVERITY.items() if s == "critical"}


def make_flag(check: str, type: str, message: str, sentence_index: int | None = None, doc_ids=None) -> Flag:
    return Flag(check=check, type=type, severity=SEVERITY[type], message=message,
                sentence_index=sentence_index, doc_ids=doc_ids or [])


def decide(flags: list[Flag]) -> str:
    if any(f.severity == "critical" or f.type in CRITICAL_TYPES for f in flags):
        return "Red"
    if any(f.severity == "warning" for f in flags):
        return "Amber"
    return "Green"


def route(verdict: str, retried: bool) -> str:
    """Where the answer goes next: employee | retry | review. Never more than one retry."""
    if verdict == "Green":
        return "employee"
    if verdict == "Amber" and not retried:
        return "retry"
    return "review"
