"""Every LLM prompt in one place, so they are easy to tune.

Each entry has a system prompt and a user template. Templates use
{placeholders} filled from the task payload; lists and dicts are inserted
as JSON. Literal braces in JSON examples are doubled: {{ }}.
"""
import json

PROMPTS: dict[str, dict[str, str]] = {
    "ping": {
        "system": "You are a connectivity check. Reply with JSON only.",
        "user": 'Reply with exactly: {{"ok": true, "provider": "openai"}}',
    },
}


def render(task: str, payload: dict) -> tuple[str, str]:
    """Return (system, user) prompts for a task, filled from the payload."""
    tpl = PROMPTS[task]
    values = {k: v if isinstance(v, str) else json.dumps(v, indent=2, ensure_ascii=False) for k, v in payload.items()}
    return tpl["system"], tpl["user"].format(**values)
