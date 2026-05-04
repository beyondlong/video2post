import os
from typing import Any

import httpx
from video2post.config import LlmSettings
from video2post.env import load_video2post_dotenv
from video2post.llm.cleaning import clean_llm_output


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        settings: LlmSettings,
        http_client: Any | None = None,
    ) -> None:
        load_video2post_dotenv()
        self.settings = settings
        self.model_name = settings.model or os.getenv("VIDEO2POST_LLM_MODEL") or ""
        self._http_client = http_client or httpx.Client()

    def generate(self, prompt: str) -> str:
        api_key = os.getenv("VIDEO2POST_LLM_API_KEY")
        base_url = self.settings.base_url or os.getenv("VIDEO2POST_LLM_BASE_URL")
        model = self.settings.model or os.getenv("VIDEO2POST_LLM_MODEL")
        if not api_key:
            raise RuntimeError("Missing VIDEO2POST_LLM_API_KEY environment variable.")
        if not base_url:
            raise RuntimeError("Missing llm.base_url configuration.")
        if not model:
            raise RuntimeError("Missing llm.model configuration.")
        attempts = max(self.settings.retry_attempts, 1)
        last_error: httpx.HTTPError | None = None

        for _ in range(attempts):
            try:
                response = self._http_client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": self.settings.temperature,
                        "max_tokens": self.settings.max_tokens,
                    },
                    timeout=self.settings.request_timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()
                return clean_llm_output(data["choices"][0]["message"]["content"])
            except (httpx.ReadTimeout, httpx.RemoteProtocolError) as error:
                last_error = error

        if last_error is not None:
            raise last_error
        raise RuntimeError("OpenAI-compatible provider failed without returning a response.")
