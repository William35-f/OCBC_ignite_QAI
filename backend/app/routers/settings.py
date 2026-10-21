"""Settings page: LLM provider, similarity threshold, max follow-up questions."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from app.core.llm import call_json, get_provider
from app.core.llm.openai_provider import is_configured
from app.core.runtime import RuntimeSettings, get_runtime, update_runtime
from app.schemas.kb import SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsOut(RuntimeSettings):
    openai_configured: bool = False


class Ping(BaseModel):
    ok: bool
    provider: str = ""


@router.get("", response_model=SettingsOut)
def read_settings():
    return SettingsOut(**get_runtime().model_dump(), openai_configured=is_configured())


@router.put("", response_model=SettingsOut)
def write_settings(body: SettingsUpdate):
    if body.llm_provider and body.llm_provider not in ("mock", "openai"):
        raise HTTPException(400, "llm_provider must be 'mock' or 'openai'")
    try:
        new = update_runtime(body.model_dump())
    except ValidationError as e:
        raise HTTPException(400, str(e)) from e
    return SettingsOut(**new.model_dump(), openai_configured=is_configured())


@router.post("/test")
async def test_provider():
    """Send a tiny JSON request to the selected provider."""
    try:
        result = await call_json("ping", {}, Ping, provider=get_provider())
        return {"ok": result.ok, "provider": get_runtime().llm_provider}
    except Exception as e:  # show the error on the Settings page
        return {"ok": False, "provider": get_runtime().llm_provider, "error": str(e)[:300]}
