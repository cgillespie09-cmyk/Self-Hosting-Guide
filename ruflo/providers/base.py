from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def complete(self, messages: list[dict], model: str = None, max_tokens: int = 4096) -> LLMResponse:
        pass

    @abstractmethod
    async def stream(self, messages: list[dict], model: str = None) -> AsyncIterator[str]:
        pass
