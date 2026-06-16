from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentResult:
    output: str
    success: bool
    tokens_used: int = 0
    metadata: dict = field(default_factory=dict)
    error: Optional[str] = None


class BaseAgent(ABC):
    name: str = "base"
    description: str = ""
    skills: list[str] = []

    def __init__(self, provider, memory):
        self.provider = provider
        self.memory = memory

    @abstractmethod
    async def run(self, task: str, context: list[dict] = None) -> AgentResult:
        pass

    def _build_system_prompt(self) -> str:
        return f"You are {self.name}. {self.description}"

    def _build_messages(self, task: str, context: list[dict] = None) -> list[dict]:
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        if context:
            for item in context:
                role = item.get("role", "user")
                content = item.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": task})
        return messages
