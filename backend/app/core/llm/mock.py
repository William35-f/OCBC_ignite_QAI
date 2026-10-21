"""Mock LLM provider: deterministic, no API key, no internet.

Each task (prompt_check, ocbc_answer, label_claims, ...) has a small
rule-based handler registered with @mock_handler. Handlers read the
structured `payload` rather than the prompt text, and return either a
dict (sent back as JSON, so it still goes through Pydantic validation) or
a string (for free-text answers).

Handlers for each workflow step are added in their own build phase.
"""
import json
from collections.abc import Callable

from app.core.llm.base import LLMProvider

MockHandler = Callable[[dict], dict | str]
HANDLERS: dict[str, MockHandler] = {}


def mock_handler(task: str) -> Callable[[MockHandler], MockHandler]:
    def register(fn: MockHandler) -> MockHandler:
        HANDLERS[task] = fn
        return fn

    return register


class MockProvider(LLMProvider):
    name = "mock"

    async def complete(self, task: str, system: str, user: str, payload: dict, json_mode: bool) -> str:
        handler = HANDLERS.get(task)
        if handler is None:
            raise KeyError(f"mock provider has no handler for task '{task}'")
        result = handler(payload)
        return json.dumps(result) if isinstance(result, dict) else str(result)


@mock_handler("ping")
def _ping(payload: dict) -> dict:
    return {"ok": True, "provider": "mock"}
