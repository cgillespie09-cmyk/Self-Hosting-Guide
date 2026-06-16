import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruflo.agents.base import AgentResult
    from ruflo.providers.base import BaseProvider
    from ruflo.memory.store import MemoryStore

_SCORE_PROMPT = """Rate the quality of this AI response for the given task on a scale of 1-10.

Task: {task}

Response (first 500 chars): {response}

Scoring criteria:
- 9-10: Excellent, complete, accurate, well-structured
- 7-8: Good, mostly complete, minor issues
- 5-6: Adequate, partially addresses the task
- 3-4: Poor, significant gaps or errors
- 1-2: Very poor, irrelevant or failed

Return ONLY JSON: {{"score": 7, "reason": "brief reason"}}
JSON:"""


def _extract_score(text: str) -> float:
    """Robustly extract numeric score from LLM JSON response."""
    text = text.strip()
    try:
        data = json.loads(text)
        return float(data.get("score", 5.0))
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Try regex for JSON-like score
    match = re.search(r'"score"\s*:\s*(\d+(?:\.\d+)?)', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    # Try to find standalone number 1-10
    match2 = re.search(r'\b([1-9]|10)\b', text)
    if match2:
        try:
            return float(match2.group(1))
        except ValueError:
            pass

    return 5.0


class LearningLoop:
    def __init__(self, provider: "BaseProvider", memory: "MemoryStore"):
        self.provider = provider
        self.memory = memory

    async def record(
        self,
        task: str,
        agent_name: str,
        result: "AgentResult",
        latency_ms: float = 0.0,
    ):
        """Score result and persist to memory, update routing weights."""
        score = await self.score_result(task, result)

        await self.memory.log_task_result(
            task=task,
            agent_used=agent_name,
            success_score=score,
            latency_ms=latency_ms,
            tokens_used=result.tokens_used if result else 0,
        )

        task_type = self._classify_task(task)
        success = score >= 6.0
        await self.memory.update_route_weight(agent_name, task_type, success)

    async def score_result(self, task: str, result: "AgentResult") -> float:
        """Ask LLM to score the result quality 1-10."""
        if result is None:
            return 1.0
        if not result.success:
            return 1.0
        if not result.output or result.output.strip() == "":
            return 1.0

        try:
            prompt = _SCORE_PROMPT.format(
                task=task[:300],
                response=result.output[:500],
            )
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a quality evaluator. Respond with ONLY a JSON object "
                        "containing a numeric score 1-10 and brief reason. No other text."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
            eval_result = await self.provider.complete(messages, max_tokens=100)
            score = _extract_score(eval_result.content)
            return max(1.0, min(10.0, score))
        except Exception:
            # If scoring fails, give a neutral score for successful results
            return 5.0

    def _classify_task(self, task: str) -> str:
        task_lower = task.lower()
        if any(w in task_lower for w in ["code", "script", "program", "debug", "python", "javascript", "function"]):
            return "coding"
        elif any(w in task_lower for w in ["search", "research", "find", "look up", "what is", "who is", "explain"]):
            return "research"
        elif any(w in task_lower for w in ["write", "draft", "email", "post", "blog", "pitch", "essay", "article"]):
            return "writing"
        elif any(w in task_lower for w in ["scrape", "extract", "crawl", "leads"]):
            return "scraping"
        return "general"

    async def get_stats(self) -> list[dict]:
        """Return aggregate stats per agent from task history."""
        return await self.memory.get_stats()

    async def optimize_prompt(self, agent_name: str) -> str:
        """Analyze recent failures and suggest prompt improvements."""
        try:
            failures = await self.memory.get_recent_failures(agent_name, limit=5)
            if not failures:
                return f"No recent failures found for {agent_name}. Agent is performing well."

            failure_summary = "\n".join(
                [
                    f"- Task: {f['task'][:100]} | Score: {f['success_score']:.1f}"
                    for f in failures
                ]
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are an AI prompt engineering expert.",
                },
                {
                    "role": "user",
                    "content": (
                        f"The '{agent_name}' AI agent has been struggling with these tasks recently:\n\n"
                        f"{failure_summary}\n\n"
                        f"Suggest 3-5 specific improvements to make to the agent's system prompt "
                        f"or approach to handle these types of tasks better. Be concrete and actionable."
                    ),
                },
            ]
            result = await self.provider.complete(messages, max_tokens=800)
            return result.content
        except Exception as e:
            return f"Could not generate optimization suggestions: {str(e)}"
