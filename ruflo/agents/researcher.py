import os
from typing import Optional

from .base import BaseAgent, AgentResult

_SYSTEM_PROMPT = (
    "You are an expert research assistant. Your job is to find, synthesize, and summarize "
    "information accurately. When given research results, extract the key facts and present "
    "them in a clear, well-structured format with source attribution where possible. "
    "If you are answering from your own knowledge, be transparent about that."
)


class ResearcherAgent(BaseAgent):
    name: str = "researcher"
    description: str = "Research assistant that finds and summarizes information from the web or knowledge base."
    skills: list[str] = ["research", "search", "summarize", "web", "find information"]

    def _build_system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    async def run(self, task: str, context: list[dict] = None) -> AgentResult:
        try:
            firecrawl_key = os.environ.get("FIRECRAWL_API_KEY", "")
            firecrawl_available = False

            try:
                from firecrawl import FirecrawlApp
                if firecrawl_key:
                    firecrawl_available = True
            except ImportError:
                pass

            if firecrawl_available:
                return await self._run_with_firecrawl(task, context, firecrawl_key)
            else:
                return await self._run_with_llm_only(task, context)

        except Exception as e:
            return AgentResult(
                output=f"Research failed: {str(e)}",
                success=False,
                error=str(e),
            )

    async def _run_with_firecrawl(
        self, task: str, context: list[dict], api_key: str
    ) -> AgentResult:
        try:
            from firecrawl import FirecrawlApp

            app = FirecrawlApp(api_key=api_key)
            results = app.search(task, limit=5)

            # Format raw search results
            raw_snippets = []
            if hasattr(results, "data") and results.data:
                for item in results.data[:5]:
                    title = getattr(item, "title", "") or item.get("title", "")
                    url = getattr(item, "url", "") or item.get("url", "")
                    content = getattr(item, "markdown", "") or item.get("markdown", "") or getattr(item, "content", "") or item.get("content", "")
                    if content:
                        raw_snippets.append(f"### {title}\nURL: {url}\n{content[:800]}")
            elif isinstance(results, list):
                for item in results[:5]:
                    if isinstance(item, dict):
                        title = item.get("title", "")
                        url = item.get("url", "")
                        content = item.get("markdown", "") or item.get("content", "")
                        if content:
                            raw_snippets.append(f"### {title}\nURL: {url}\n{content[:800]}")

            if not raw_snippets:
                return await self._run_with_llm_only(task, context)

            combined = "\n\n---\n\n".join(raw_snippets)
            summarize_prompt = (
                f"Based on the following web search results, provide a comprehensive answer to:\n\n"
                f"**Task/Question:** {task}\n\n"
                f"**Search Results:**\n{combined}\n\n"
                f"Synthesize a clear, accurate summary with key facts and cite sources where relevant."
            )

            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": summarize_prompt},
            ]

            result = await self.provider.complete(messages, max_tokens=2048)
            return AgentResult(
                output=result.content,
                success=True,
                tokens_used=result.input_tokens + result.output_tokens,
                metadata={"source": "firecrawl+llm", "snippets_count": len(raw_snippets)},
            )

        except Exception as e:
            # Fall back to LLM-only if firecrawl fails
            return await self._run_with_llm_only(task, context)

    async def _run_with_llm_only(self, task: str, context: list[dict] = None) -> AgentResult:
        messages = self._build_messages(task, context)
        result = await self.provider.complete(messages, max_tokens=2048)
        return AgentResult(
            output=result.content,
            success=True,
            tokens_used=result.input_tokens + result.output_tokens,
            metadata={"source": "llm_knowledge"},
        )
