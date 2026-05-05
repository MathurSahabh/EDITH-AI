from typing import Optional
import asyncio

from openai import AsyncOpenAI


class OpenRouterClient:
    def __init__(self, config):
        self.config = config
        base_url = getattr(config, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.client = AsyncOpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=base_url,
            default_headers=self._default_headers(),
        )
        self.model = getattr(config, "OPENROUTER_MODEL", "openai/gpt-4o-mini")
        self.timeout_sec = getattr(config, "REQUEST_TIMEOUT_SEC", 30)

    def _default_headers(self):
        headers = {}
        site_url = getattr(self.config, "OPENROUTER_SITE_URL", "")
        app_name = getattr(self.config, "OPENROUTER_APP_NAME", "")
        if site_url:
            headers["HTTP-Referer"] = site_url
        if app_name:
            headers["X-Title"] = app_name
        return headers

    async def chat(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Simple single-shot chat interface.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async def _call():
            res = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
            )
            return (res.choices[0].message.content or "").strip()

        try:
            return await asyncio.wait_for(_call(), timeout=self.timeout_sec)
        except Exception as e:
            return f"LLM error: {e}"
