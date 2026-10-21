"""Runtime settings that the Settings page can change (stored in the DB).

Defaults come from backend/.env (see config.py).
"""
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import AppSetting

KEY = "runtime"


class RuntimeSettings(BaseModel):
    llm_provider: str = Field(default_factory=lambda: settings.llm_provider)  # mock | openai
    similarity_threshold: float = Field(default_factory=lambda: settings.similarity_threshold, ge=0, le=1)
    max_followups: int = Field(default_factory=lambda: settings.max_followups, ge=0, le=2)


def get_runtime() -> RuntimeSettings:
    with SessionLocal() as db:
        row = db.get(AppSetting, KEY)
        return RuntimeSettings(**(row.value if row else {}))


def update_runtime(changes: dict) -> RuntimeSettings:
    new = get_runtime().model_copy(update={k: v for k, v in changes.items() if v is not None})
    new = RuntimeSettings.model_validate(new.model_dump())  # re-run validation
    with SessionLocal() as db:
        row = db.get(AppSetting, KEY)
        if row is None:
            db.add(AppSetting(key=KEY, value=new.model_dump()))
        else:
            row.value = new.model_dump()
        db.commit()
    return new
