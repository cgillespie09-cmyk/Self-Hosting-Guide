import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruflo.providers.base import BaseProvider
    from ruflo.memory.store import MemoryStore

_AGENT_SKILLS = {
    "researcher": "research, search, summarize, web, find information",
    "coder": "code, programming, debug, script, python, javascript",
    "writer": "write, email, content, blog, pitch, draft, copy",
    "scraper": "scrape, extract, crawl, leads, data extraction",
}

_ROUTE_PROMPT_TEMPLATE = """Given this task: '{task}', score each agent (0-10) based on how well their skills match.

Agent skills:
- researcher: research, search, summarize, web, find information
- coder: code, programming, debug, script, python, javascript
- writer: write, email, content, blog, pitch, draft, copy
- scraper: scrape, extract, crawl, leads, data extraction

Return ONLY a JSON object with agent names as keys and integer scores (0-10) as values.
Example: {{"researcher": 7, "coder": 2, "writer": 1, "scraper": 3}}

Task: {task}
JSON scores:"""


def _extract_json(text: str) -> dict:
    """Robustly extract JSON dict from LLM response."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {}


def _keyword_scores(task: str) -> dict[str, float]:
    """Fast keyword-based fallback scoring."""
    task_lower = task.lower()
    scores = {name: 1.0 for name in _AGENT_SKILLS}

    if any(w in task_lower for w in ["code", "script", "program", "debug", "function", "python", "javascript", "algorithm"]):
        scores["coder"] += 7
    if any(w in task_lower for w in ["research", "search", "find", "look up", "what is", "who is", "summarize", "explain"]):
        scores["researcher"] += 7
    if any(w in task_lower for w in ["write", "draft", "email", "post", "blog", "pitch", "essay", "article", "copy"]):
        scores["writer"] += 7
    if any(w in task_lower for w in ["scrape", "extract", "crawl", "leads", "data from", "get data"]):
        scores["scraper"] += 7

    return scores


class Router:
    def __init__(self, provider: "BaseProvider", memory: "MemoryStore"):
        self.provider = provider
        self.memory = memory

    async def route(self, task: str) -> list[str]:
        """Return ranked list of agent names for the given task."""
        # 1. Determine task type for historical lookup
        task_type = self._classify_task_type(task)

        # 2. Get historical weights from memory
        historical = {}
        try:
            historical = await self.memory.get_route_weights(task_type)
        except Exception:
            historical = {}

        # 3. Get LLM scores
        llm_scores = await self._llm_scores(task)

        # 4. Blend scores
        blended = {}
        for agent in ["researcher", "coder", "writer", "scraper"]:
            llm_score = llm_scores.get(agent, 3.0)
            hist = historical.get(agent, {})
            attempts = hist.get("attempts", 0)
            hist_weight = hist.get("weight", 5.0)

            if attempts >= 10:
                # Enough history — blend 70% historical, 30% LLM
                blended[agent] = 0.7 * hist_weight + 0.3 * llm_score
            else:
                # Not enough history — use LLM primarily
                blended[agent] = llm_score

        # 5. Sort descending by score
        ranked = sorted(blended.items(), key=lambda x: x[1], reverse=True)
        return [name for name, _ in ranked]

    async def _llm_scores(self, task: str) -> dict[str, float]:
        """Ask the LLM to score agents for this task."""
        try:
            prompt = _ROUTE_PROMPT_TEMPLATE.format(task=task)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a task router. Respond with ONLY a JSON object containing "
                        "agent scores as integers 0-10. No explanation, no markdown, just JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
            result = await self.provider.complete(messages, max_tokens=150)
            parsed = _extract_json(result.content)

            # Validate and normalize
            scores = {}
            for agent in ["researcher", "coder", "writer", "scraper"]:
                raw = parsed.get(agent, 3)
                try:
                    scores[agent] = max(0.0, min(10.0, float(raw)))
                except (TypeError, ValueError):
                    scores[agent] = 3.0
            return scores

        except Exception:
            # Fall back to keyword scoring
            return _keyword_scores(task)

    def _classify_task_type(self, task: str) -> str:
        task_lower = task.lower()
        if any(w in task_lower for w in ["code", "script", "program", "debug", "python", "javascript"]):
            return "coding"
        elif any(w in task_lower for w in ["search", "research", "find", "look up", "what is", "who is"]):
            return "research"
        elif any(w in task_lower for w in ["write", "draft", "email", "post", "blog", "pitch"]):
            return "writing"
        elif any(w in task_lower for w in ["scrape", "extract", "crawl", "leads"]):
            return "scraping"
        return "general"
