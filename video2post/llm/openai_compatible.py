import os
from typing import Any

import httpx

from video2post.config import LlmSettings


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        settings: LlmSettings,
        http_client: Any | None = None,
    ) -> None:
        self.settings = settings
        self.model_name = settings.model or ""
        self._http_client = http_client or httpx.Client()

    def generate(self, prompt: str) -> str:
        api_key = os.getenv("VIDEO2POST_LLM_API_KEY")
        if not api_key:
            raise RuntimeError("Missing VIDEO2POST_LLM_API_KEY environment variable.")
        if not self.settings.base_url:
            raise RuntimeError("Missing llm.base_url configuration.")
        if not self.settings.model:
            raise RuntimeError("Missing llm.model configuration.")

        response = self._http_client.post(
            f"{self.settings.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_tokens,
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
