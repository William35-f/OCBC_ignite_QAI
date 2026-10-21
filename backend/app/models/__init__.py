"""Importing this package registers every table with SQLAlchemy."""
from app.models.improve import AppSetting, FixAction, RetestRun, TrustResult
from app.models.knowledge import Conflict, Document
from app.models.review import GoldenItem, ReviewItem
from app.models.workflow import EventLog, Run

__all__ = [
    "AppSetting",
    "Conflict",
    "Document",
    "EventLog",
    "FixAction",
    "GoldenItem",
    "RetestRun",
    "ReviewItem",
    "Run",
    "TrustResult",
]
