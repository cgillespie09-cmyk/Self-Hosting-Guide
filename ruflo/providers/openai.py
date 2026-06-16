import os
from typing import AsyncIterator
from .base import BaseProvider, LLMResponse


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self):
        self.default_model = "gpt-4o"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
        return self._client

    async def complete(self, messages: list[dict], model: str = None, max_tokens: int = 4096) -> LLMResponse:
        client = self._get_client()
        model = model or self.default_model
        response = await client.chat.completions.create(
            model=model, max_tokens=max_tokens, messages=messages
        )
        return LLMResponse(
            content=response.choices[0].message.content,
            model=model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )

    async def stream(self, messages: list[dict], model: str = None) -> AsyncIterator[str]:
        client = self._get_client()
        model = model or self.default_model
        async for chunk in await client.chat.completions.create(
            model=model, messages=messages, stream=True
        ):
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
