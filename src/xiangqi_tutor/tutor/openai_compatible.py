from __future__ import annotations

import asyncio
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from xiangqi_tutor.tutor.provider import LLMProvider, TutorRequest


class LLMProviderError(RuntimeError):
    """可安全展示给 GUI 的模型调用错误，不包含密钥或完整响应头。"""


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 1200,
        timeout_seconds: float = 30,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 2,
    ) -> None:
        parsed = urlparse(base_url)
        local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not local_http:
            raise ValueError("模型 API 必须使用 HTTPS；仅本机服务允许 HTTP")
        if not api_key.strip() or not model.strip():
            raise ValueError("API Key 和模型名称不能为空")
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self._transport = transport
        self.max_retries = max(0, max_retries)
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds, transport=self._transport)
        return self._client

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def complete(self, request: TutorRequest) -> dict[str, object]:
        system_prompt = str(request.context.get("system_prompt", ""))
        user_prompt = str(request.context.get("user_prompt", ""))
        if not system_prompt or not user_prompt:
            raise LLMProviderError("导师请求缺少系统提示词或局面数据")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        started = time.perf_counter()
        try:
            response = None
            for attempt in range(self.max_retries + 1):
                try:
                    response = await self._get_client().post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self._api_key}"},
                        json=payload,
                    )
                    if response.status_code != 429 and response.status_code < 500:
                        break
                except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
                    if attempt >= self.max_retries:
                        raise
                if attempt < self.max_retries:
                    await asyncio.sleep(0.25 * (2**attempt))
            assert response is not None
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            content = data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderError("模型服务暂时不可用或返回格式异常") from exc
        return {
            "model": str(data.get("model", self.model)),
            "content": str(content),
            "latency_seconds": time.perf_counter() - started,
            "usage": data.get("usage", {}),
        }

    async def test_connection(self) -> tuple[str, float]:
        request = TutorRequest(
            task="connection_test",
            context={
                "system_prompt": "你只需回复 OK。",
                "user_prompt": "连接测试",
            },
        )
        result = await self.complete(request)
        return str(result["model"]), float(result["latency_seconds"])
