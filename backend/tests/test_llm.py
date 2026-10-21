"""LLM layer: JSON replies are validated with Pydantic and retried once."""
import pytest
from pydantic import BaseModel

from app.core.llm import LLMOutputError, call_json, get_provider
from app.core.llm.base import LLMProvider


class Ping(BaseModel):
    ok: bool
    provider: str


class ScriptedProvider(LLMProvider):
    """Returns the scripted replies in order and counts calls."""

    name = "scripted"

    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0

    async def complete(self, task, system, user, payload, json_mode):
        self.calls += 1
        return self.replies.pop(0)


async def test_mock_provider_is_default_and_valid():
    result = await call_json("ping", {}, Ping, provider=get_provider("mock"))
    assert result.ok and result.provider == "mock"


async def test_retry_once_on_invalid_json():
    p = ScriptedProvider(["not json", '{"ok": true, "provider": "x"}'])
    result = await call_json("ping", {}, Ping, provider=p)
    assert result.ok and p.calls == 2


async def test_code_fences_are_tolerated():
    p = ScriptedProvider(['```json\n{"ok": true, "provider": "x"}\n```'])
    assert (await call_json("ping", {}, Ping, provider=p)).ok


async def test_gives_up_after_one_retry():
    p = ScriptedProvider(['{"ok": "maybe"}', "still not json", "never reached"])
    with pytest.raises(LLMOutputError):
        await call_json("ping", {}, Ping, provider=p)
    assert p.calls == 2
