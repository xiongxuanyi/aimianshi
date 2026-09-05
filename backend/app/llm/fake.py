"""测试用 Fake LLM 客户端。"""
from typing import Any

from app.llm.base import ChatMessage, LLMClient


class FakeLLMClient(LLMClient):
    """返回可编程的脚本化响应，记录调用，供单元测试断言。"""

    def __init__(self, reply: str = "", json_reply: dict[str, Any] | None = None):
        self.reply = reply
        self.json_reply = json_reply or {}
        self.chat_calls: list[list[ChatMessage]] = []
        self.json_calls: list[list[ChatMessage]] = []

    def chat(self, messages: list[ChatMessage], temperature: float = 0.7) -> str:
        self.chat_calls.append(messages)
        return self.reply

    def chat_json(self, messages: list[ChatMessage], temperature: float = 0.2) -> dict[str, Any]:
        self.json_calls.append(messages)
        return self.json_reply
