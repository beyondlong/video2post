import json

from video2post.config import LlmSettings
from video2post.llm.openai_compatible import OpenAICompatibleProvider


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
                            "content": "Generated content",
                        }
                    }
                ]
            }
        )


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


def test_openai_compatible_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("VIDEO2POST_LLM_API_KEY", raising=False)
    provider = OpenAICompatibleProvider(
        settings=LlmSettings(base_url="https://llm.example.com/v1", model="test-model")
    )

    try:
        provider.generate("Hello")
    except RuntimeError as error:
        assert "VIDEO2POST_LLM_API_KEY" in str(error)
    else:
        raise AssertionError("Expected missing API key error")
