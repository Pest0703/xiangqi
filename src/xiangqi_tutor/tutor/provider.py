from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TutorRequest:
    task: str
    context: dict[str, object]
    question: str = ""


class LLMProvider(ABC):
    """厂商无关的导师模型边界。模型只解释已有棋理证据，不计算最佳着。"""

    @abstractmethod
    async def complete(self, request: TutorRequest) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    async def test_connection(self) -> tuple[str, float]:
        raise NotImplementedError

