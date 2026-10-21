"""Real LLM provider: Azure OpenAI or OpenAI, configured in backend/.env.

If AZURE_OPENAI_ENDPOINT is set we use Azure, otherwise plain OpenAI.
"""
from app.core.config import settings
from app.core.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        from openai import AsyncAzureOpenAI, AsyncOpenAI

        if settings.azure_openai_endpoint:
            self.client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
            self.model = settings.azure_openai_deployment  # Azure uses the deployment name
        else:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key or None)
            self.model = settings.openai_model

    async def complete(self, task: str, system: str, user: str, payload: dict, json_mode: bool) -> str:
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        resp = await self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            **kwargs,
        )
        return resp.choices[0].message.content or ""


def is_configured() -> bool:
    if settings.azure_openai_endpoint:
        return bool(settings.azure_openai_api_key and settings.azure_openai_deployment)
    return bool(settings.openai_api_key)
