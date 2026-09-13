import asyncio
import json

import httpx
import pytest

from xiangqi_tutor.tutor.openai_compatible import LLMProviderError, OpenAICompatibleProvider
from xiangqi_tutor.tutor.provider import TutorRequest


def make_request() -> TutorRequest:
    return TutorRequest(
        task="test",
        context={"system_prompt": "system", "user_prompt": "user"},
    )


def test_provider_sends_openai_compatible_request_without_leaking_key() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer secret-key"
        body = json.loads(request.content)
        assert body["model"] == "qwen-plus"
        return httpx.Response(
            200,
            json={"model": "qwen-plus", "choices": [{"message": {"content": "OK"}}]},
        )

    provider = OpenAICompatibleProvider(
        base_url="https://example.test/v1",
        api_key="secret-key",
        model="qwen-plus",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(provider.complete(make_request()))
    assert result["content"] == "OK"
    assert "secret-key" not in repr(result)


def test_provider_converts_remote_error_to_safe_error() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "secret diagnostic"}})

    provider = OpenAICompatibleProvider(
        base_url="https://example.test/v1",
        api_key="secret-key",
        model="qwen-plus",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(LLMProviderError, match="暂时不可用") as caught:
        asyncio.run(provider.complete(make_request()))
    assert "secret-key" not in str(caught.value)
    assert "secret diagnostic" not in str(caught.value)


def test_provider_allows_local_http_and_retries_429() -> None:
    calls = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, json={"error": "busy"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    provider = OpenAICompatibleProvider(
        base_url="http://127.0.0.1:11434/v1",
        api_key="local",
        model="qwen",
        transport=httpx.MockTransport(handler),
        max_retries=1,
    )
    assert asyncio.run(provider.complete(make_request()))["content"] == "OK"
    assert calls == 2
