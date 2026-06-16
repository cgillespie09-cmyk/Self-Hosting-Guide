from .base import BaseAgent, AgentResult

_SYSTEM_PROMPT = (
    "You are an expert creative and professional writer. You craft clear, engaging, and "
    "audience-appropriate content. Whether writing blog posts, emails, marketing copy, "
    "social media posts, pitches, or long-form articles, you adapt your tone and style "
    "to the context. You prioritize clarity, flow, and impact. "
    "Structure your writing with appropriate headings, paragraphs, and formatting. "
    "Make every word count."
)


class WriterAgent(BaseAgent):
    name: str = "writer"
    description: str = "Creative and professional writer for all content types."
    skills: list[str] = ["write", "email", "content", "blog", "pitch", "draft", "copy"]

    def _build_system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    async def run(self, task: str, context: list[dict] = None) -> AgentResult:
        try:
            messages = self._build_messages(task, context)
            result = await self.provider.complete(messages, max_tokens=3000)
            return AgentResult(
                output=result.content,
                success=True,
                tokens_used=result.input_tokens + result.output_tokens,
                metadata={"model": result.model},
            )
        except Exception as e:
            return AgentResult(
                output=f"Writing task failed: {str(e)}",
                success=False,
                error=str(e),
            )
