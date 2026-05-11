import os
from typing import Any

import httpx
from video2post.config import LlmSettings
from video2post.env import load_video2post_dotenv
from video2post.llm.cleaning import clean_llm_output


class LlmProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str = "",
        provider_error_type: str | None = None,
        provider_error_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.provider_error_type = provider_error_type
        self.provider_error_message = provider_error_message


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
            except httpx.HTTPStatusError as error:
                body = error.response.text.strip()
                provider_error_type = None
                provider_error_message = None
                if body:
                    try:
                        error_payload = error.response.json()
                    except ValueError:
                        error_payload = {}
                    provider_error = error_payload.get("error") if isinstance(error_payload, dict) else None
                    if isinstance(provider_error, dict):
                        provider_error_type = provider_error.get("type")
                        provider_error_message = provider_error.get("message")
                detail = f" Response body: {body[:2000]}" if body else ""
                raise LlmProviderError(
                    f"LLM request failed with HTTP {error.response.status_code}: {error}.{detail}",
                    status_code=error.response.status_code,
                    response_body=body,
                    provider_error_type=provider_error_type,
                    provider_error_message=provider_error_message,
                ) from error
            except (httpx.ReadTimeout, httpx.RemoteProtocolError) as error:
                last_error = error

        if last_error is not None:
            raise last_error
        raise RuntimeError("OpenAI-compatible provider failed without returning a response.")
