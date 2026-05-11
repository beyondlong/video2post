import json

import httpx
from pathlib import Path

from video2post.config import LlmSettings
from video2post.llm.openai_compatible import LlmProviderError, OpenAICompatibleProvider


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self):
        self.requests = []

    def post(self, url, *, headers, json, timeout):
        self.requests.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "<think>hidden</think>\n\nGenerated content",
                        }
                    }
                ]
            }
        )




class HttpErrorResponse:
    text = '{"error":{"type":"unprocessable_entity_error","message":"prompt rejected"}}'

    def raise_for_status(self):
        request = httpx.Request("POST", "https://llm.example.com/v1/chat/completions")
        response = httpx.Response(422, request=request, text=self.text)
        raise httpx.HTTPStatusError("unprocessable", request=request, response=response)

    def json(self):
        return {}


class HttpErrorClient:
    def __init__(self):
        self.requests = []

    def post(self, url, *, headers, json, timeout):
        self.requests.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return HttpErrorResponse()


class FlakyHttpClient:
    def __init__(self, failures, payload=None):
        self.failures = list(failures)
        self.requests = []
        self.payload = payload or {
            "choices": [
                {
                    "message": {
                        "content": "Recovered content",
                    }
                }
            ]
        }

    def post(self, url, *, headers, json, timeout):
        self.requests.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        if self.failures:
            raise self.failures.pop(0)
        return FakeResponse(self.payload)


def test_openai_compatible_provider_posts_chat_completion(monkeypatch):
    monkeypatch.setenv("VIDEO2POST_LLM_API_KEY", "test-key")
    client = FakeHttpClient()
    provider = OpenAICompatibleProvider(
        settings=LlmSettings(
            base_url="https://llm.example.com/v1",
            model="test-model",
            temperature=0.2,
            max_tokens=123,
        ),
        http_client=client,
    )

    result = provider.generate("Hello prompt")

    assert result == "Generated content"
    request = client.requests[0]
    assert request["url"] == "https://llm.example.com/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["json"] == {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello prompt"}],
        "temperature": 0.2,
        "max_tokens": 123,
    }
    assert request["timeout"] == 300


def test_openai_compatible_provider_uses_configured_timeout(monkeypatch):
    monkeypatch.setenv("VIDEO2POST_LLM_API_KEY", "test-key")
    client = FakeHttpClient()
    provider = OpenAICompatibleProvider(
        settings=LlmSettings(
            base_url="https://llm.example.com/v1",
            model="test-model",
            request_timeout_seconds=300,
        ),
        http_client=client,
    )

    provider.generate("Hello prompt")

    assert client.requests[0]["timeout"] == 300


def test_openai_compatible_provider_retries_transient_transport_errors(monkeypatch):
    monkeypatch.setenv("VIDEO2POST_LLM_API_KEY", "test-key")
    client = FlakyHttpClient(
        failures=[
            httpx.ReadTimeout("timed out"),
            httpx.RemoteProtocolError("disconnected"),
        ]
    )
    provider = OpenAICompatibleProvider(
        settings=LlmSettings(
            base_url="https://llm.example.com/v1",
            model="test-model",
            retry_attempts=3,
        ),
        http_client=client,
    )

    result = provider.generate("Hello prompt")

    assert result == "Recovered content"
    assert len(client.requests) == 3


def test_openai_compatible_provider_raises_after_retry_budget_exhausted(monkeypatch):
    monkeypatch.setenv("VIDEO2POST_LLM_API_KEY", "test-key")
    client = FlakyHttpClient(failures=[httpx.ReadTimeout("timed out")] * 3)
    provider = OpenAICompatibleProvider(
        settings=LlmSettings(
            base_url="https://llm.example.com/v1",
            model="test-model",
            retry_attempts=3,
        ),
        http_client=client,
    )

    try:
        provider.generate("Hello prompt")
    except httpx.ReadTimeout:
        pass
    else:
        raise AssertionError("Expected ReadTimeout after retries are exhausted")

    assert len(client.requests) == 3


def test_openai_compatible_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("VIDEO2POST_LLM_API_KEY", raising=False)
    monkeypatch.delenv("VIDEO2POST_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("VIDEO2POST_LLM_MODEL", raising=False)
    monkeypatch.chdir("/")
    monkeypatch.setattr("video2post.env._dotenv_paths", lambda: [])
    provider = OpenAICompatibleProvider(
        settings=LlmSettings(base_url="https://llm.example.com/v1", model="test-model")
    )

    try:
        provider.generate("Hello")
    except RuntimeError as error:
        assert "VIDEO2POST_LLM_API_KEY" in str(error)
    else:
        raise AssertionError("Expected missing API key error")


def test_openai_compatible_provider_loads_project_dotenv_from_other_working_directory(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("VIDEO2POST_LLM_API_KEY", raising=False)
    monkeypatch.delenv("VIDEO2POST_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("VIDEO2POST_LLM_MODEL", raising=False)
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    project_env = tmp_path / "project.env"
    project_env.write_text(
        "\n".join(
            [
                "VIDEO2POST_LLM_API_KEY=project-key",
                "VIDEO2POST_LLM_BASE_URL=https://project.example.com/v1",
                "VIDEO2POST_LLM_MODEL=project-model",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(work_dir)
    monkeypatch.setattr(
        "video2post.env._dotenv_paths",
        lambda: [Path(".env"), project_env],
        raising=False,
    )
    client = FakeHttpClient()
    provider = OpenAICompatibleProvider(settings=LlmSettings(), http_client=client)

    result = provider.generate("Hello")

    assert result == "Generated content"
    request = client.requests[0]
    assert request["url"] == "https://project.example.com/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer project-key"
    assert request["json"]["model"] == "project-model"
    assert provider.model_name == "project-model"


def test_openai_compatible_provider_loads_dotenv_fallbacks(tmp_path, monkeypatch):
    monkeypatch.delenv("VIDEO2POST_LLM_API_KEY", raising=False)
    monkeypatch.delenv("VIDEO2POST_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("VIDEO2POST_LLM_MODEL", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "VIDEO2POST_LLM_API_KEY=dotenv-key",
                "VIDEO2POST_LLM_BASE_URL=https://dotenv.example.com/v1",
                "VIDEO2POST_LLM_MODEL=dotenv-model",
            ]
        ),
        encoding="utf-8",
    )
    client = FakeHttpClient()
    provider = OpenAICompatibleProvider(settings=LlmSettings(), http_client=client)

    result = provider.generate("Hello")

    assert result == "Generated content"
    request = client.requests[0]
    assert request["url"] == "https://dotenv.example.com/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer dotenv-key"
    assert request["json"]["model"] == "dotenv-model"
    assert provider.model_name == "dotenv-model"


def test_openai_compatible_provider_includes_http_error_body(monkeypatch):
    monkeypatch.setenv("VIDEO2POST_LLM_API_KEY", "test-key")
    client = HttpErrorClient()
    provider = OpenAICompatibleProvider(
        settings=LlmSettings(base_url="https://llm.example.com/v1", model="test-model"),
        http_client=client,
    )

    try:
        provider.generate("Hello prompt")
    except LlmProviderError as error:
        message = str(error)
        assert error.status_code == 422
        assert error.provider_error_type == "unprocessable_entity_error"
        assert error.provider_error_message == "prompt rejected"
    else:
        raise AssertionError("Expected HTTP error body to be surfaced")

    assert "422" in message
    assert "prompt rejected" in message
    assert len(client.requests) == 1
