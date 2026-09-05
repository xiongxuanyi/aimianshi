"""LLM 客户端抽象接口。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


class LLMClient(ABC):
    """大模型调用抽象，业务代码只依赖此接口。"""

    @abstractmethod
    def chat(self, messages: list[ChatMessage], temperature: float = 0.7) -> str:
        """普通对话补全。"""

    @abstractmethod
    def chat_json(self, messages: list[ChatMessage], temperature: float = 0.2) -> dict[str, Any]:
        """要求模型返回 JSON 对象（用于出题/评分等结构化输出）。"""
