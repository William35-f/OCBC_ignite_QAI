"""How the rest of the app talks to an LLM.

    result = await call_json("prompt_check", payload, PromptCheckResult)
    text   = await call_text("ocbc_answer", payload)

call_json validates the reply with Pydantic and retries once on invalid JSON.
"""
import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core import prompts
from app.core.llm.base import LLMOutputError, LLMProvider
from app.core.llm.mock import MockProvider

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")


def get_provider(name: str | None = None) -> LLMProvider:
    """Provider by name, or the one chosen on the Settings page."""
    if name is None:
        from app.core.runtime import get_runtime

        name = get_runtime().llm_provider
    if name == "openai":
        from app.core.llm.openai_provider import OpenAIProvider

        return OpenAIProvider()
    return MockProvider()


async def call_json(task: str, payload: dict, schema: type[T], provider: LLMProvider | None = None) -> T:
    provider = provider or get_provider()
    system, user = prompts.render(task, payload)
    last_error = ""
    for attempt in (1, 2):
        raw = await provider.complete(task, system, user, payload, json_mode=True)
        try:
            return schema.model_validate_json(_FENCE_RE.sub("", raw.strip()))
        except ValidationError as e:
            last_error = str(e)
            log.warning("Invalid JSON from %s for %s (attempt %d): %s", provider.name, task, attempt, last_error)
            user += (
                "\n\nYour previous reply was not valid JSON for the required schema."
                f"\nError: {last_error[:500]}\nReply again with valid JSON only."
            )
    raise LLMOutputError(f"{task}: invalid JSON after one retry: {last_error[:300]}")


async def call_text(task: str, payload: dict, provider: LLMProvider | None = None) -> str:
    provider = provider or get_provider()
    system, user = prompts.render(task, payload)
    return (await provider.complete(task, system, user, payload, json_mode=False)).strip()
