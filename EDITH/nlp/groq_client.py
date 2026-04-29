from typing import Optional
import asyncio

from groq import AsyncGroq


class GroqClient:
    def __init__(self, config):
        self.config = config
        self.client = AsyncGroq(api_key=config.GROQ_API_KEY)
        self.model = getattr(config, "GROQ_MODEL", "llama-3.1-8b-instant")
        self.timeout_sec = getattr(config, "REQUEST_TIMEOUT_SEC", 30)

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