import os
import re
from typing import Optional

from .base import BaseAgent, AgentResult

_SYSTEM_PROMPT = (
    "You are a data extraction and web scraping expert. When given scraped content, "
    "extract and structure the relevant data clearly. Present information in an organized, "
    "readable format. If asked to find leads or contact info, identify and list them systematically. "
    "If you cannot scrape directly, analyze what data would be available and how to get it."
)

_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")


class ScraperAgent(BaseAgent):
    name: str = "scraper"
    description: str = "Web scraping and data extraction agent using Firecrawl."
    skills: list[str] = ["scrape", "extract", "crawl", "leads", "data extraction"]

    def _build_system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def _extract_urls(self, text: str) -> list[str]:
        return _URL_PATTERN.findall(text)

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
                output=f"Scraping failed: {str(e)}",
                success=False,
                error=str(e),
            )

    async def _run_with_firecrawl(
        self, task: str, context: list[dict], api_key: str
    ) -> AgentResult:
        try:
            from firecrawl import FirecrawlApp

            app = FirecrawlApp(api_key=api_key)
            urls = self._extract_urls(task)
            scraped_sections = []

            if urls:
                for url in urls[:3]:  # Limit to 3 URLs
                    try:
                        result = app.scrape_url(url)
                        content = ""
                        if hasattr(result, "markdown"):
                            content = result.markdown or ""
                        elif isinstance(result, dict):
                            content = result.get("markdown", "") or result.get("content", "")
                        if content:
                            scraped_sections.append(
                                f"## Content from {url}\n\n{content[:2000]}"
                            )
                    except Exception as url_err:
                        scraped_sections.append(f"## {url}\n\nFailed to scrape: {url_err}")
            else:
                # No URLs in task, do a search instead
                try:
                    search_results = app.search(task, limit=3)
                    if hasattr(search_results, "data") and search_results.data:
                        for item in search_results.data[:3]:
                            title = getattr(item, "title", "") or item.get("title", "")
                            url = getattr(item, "url", "") or item.get("url", "")
                            content = (
                                getattr(item, "markdown", "")
                                or item.get("markdown", "")
                                or getattr(item, "content", "")
                                or item.get("content", "")
                            )
                            if content:
                                scraped_sections.append(
                                    f"## {title}\nURL: {url}\n\n{content[:1500]}"
                                )
                    elif isinstance(search_results, list):
                        for item in search_results[:3]:
                            if isinstance(item, dict):
                                title = item.get("title", "")
                                url = item.get("url", "")
                                content = item.get("markdown", "") or item.get("content", "")
                                if content:
                                    scraped_sections.append(
                                        f"## {title}\nURL: {url}\n\n{content[:1500]}"
                                    )
                except Exception:
                    pass

            if not scraped_sections:
                return await self._run_with_llm_only(task, context)

            combined_raw = "\n\n---\n\n".join(scraped_sections)
            extraction_prompt = (
                f"Task: {task}\n\n"
                f"Scraped content:\n\n{combined_raw}\n\n"
                f"Extract and structure the relevant data from the above content to fulfill the task. "
                f"Present it in a clear, organized format."
            )

            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": extraction_prompt},
            ]

            llm_result = await self.provider.complete(messages, max_tokens=2048)
            return AgentResult(
                output=llm_result.content,
                success=True,
                tokens_used=llm_result.input_tokens + llm_result.output_tokens,
                metadata={
                    "source": "firecrawl+llm",
                    "urls_scraped": len(urls),
                    "sections": len(scraped_sections),
                },
            )

        except Exception as e:
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
