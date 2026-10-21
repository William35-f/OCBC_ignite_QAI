"""The provider interface every LLM backend implements."""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def complete(self, task: str, system: str, user: str, payload: dict, json_mode: bool) -> str:
        """Return the model's raw text reply.

        task     - which job this is (e.g. "prompt_check"); the mock uses it to pick a rule
        system   - system prompt (from prompts.py)
        user     - user prompt (from prompts.py, already filled in)
        payload  - the structured inputs the prompts were built from (the mock reads these)
        json_mode- ask for a JSON object reply
        """


class LLMOutputError(Exception):
    """The model's reply could not be parsed/validated, even after one retry."""
