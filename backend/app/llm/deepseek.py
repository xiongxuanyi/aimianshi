"""DeepSeek 客户端（OpenAI 兼容接口，httpx 直连）。"""
import json
from typing import Any

import httpx

from app.core.config import settings
from app.llm.base import ChatMessage, LLMClient


class DeepSeekLLMClient(LLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = (base_url or settings.deepseek_base_url).rstrip("/")
        self.model = model or settings.deepseek_model

    def _post(
        self,
        messages: list[ChatMessage],
        temperature: float,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("缺少 DEEPSEEK_API_KEY，请在 .env 中配置")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": False,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def chat(self, messages: list[ChatMessage], temperature: float = 0.7) -> str:
        return self._post(messages, temperature)

    def chat_json(self, messages: list[ChatMessage], temperature: float = 0.2) -> dict[str, Any]:
        content = self._post(messages, temperature, response_format={"type": "json_object"})
        return json.loads(content)
