import os
from typing import AsyncIterator
import anthropic
from .base import BaseProvider, LLMResponse

COST_PER_1M = {"input": 3.0, "output": 15.0}  # claude-sonnet-4-6


class ClaudeProvider(BaseProvider):
    name = "claude"

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.default_model = "claude-sonnet-4-6"

    async def complete(self, messages: list[dict], model: str = None, max_tokens: int = 4096) -> LLMResponse:
        model = model or self.default_model
        response = await self.client.messages.create(
            model=model, max_tokens=max_tokens, messages=messages
        )
        inp = response.usage.input_tokens
        out = response.usage.output_tokens
        cost = (inp / 1_000_000) * COST_PER_1M["input"] + (out / 1_000_000) * COST_PER_1M["output"]
        return LLMResponse(
            content=response.content[0].text,
            model=model,
            input_tokens=inp,
            output_tokens=out,
            cost_usd=cost,
        )

    async def stream(self, messages: list[dict], model: str = None) -> AsyncIterator[str]:
        model = model or self.default_model
        async with self.client.messages.stream(model=model, max_tokens=4096, messages=messages) as s:
            async for text in s.text_stream:
                yield text
