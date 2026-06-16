import asyncio
import json
import re
from typing import TYPE_CHECKING, Literal, Union

if TYPE_CHECKING:
    from ruflo.agents.base import BaseAgent, AgentResult
    from ruflo.providers.base import BaseProvider
    from ruflo.memory.store import MemoryStore


def _extract_winner(text: str) -> str:
    """Extract 'A' or 'B' winner from LLM JSON response."""
    text = text.strip()
    # Try JSON parse
    try:
        data = json.loads(text)
        return str(data.get("winner", "A")).upper()
    except json.JSONDecodeError:
        pass

    # Regex fallback
    match = re.search(r'"winner"\s*:\s*"([AB])"', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Plain text fallback
    if "response b" in text.lower() or '"winner": "b"' in text.lower():
        return "B"
    return "A"


_BEST_OF_PROMPT = """You are a quality evaluator. Choose which response better answers the given task.

Task: {task}

Response A:
{response_a}

Response B:
{response_b}

Which response better answers the task? Return ONLY JSON: {{"winner": "A", "reason": "brief reason"}}
JSON:"""


class Swarm:
    def __init__(self, provider: "BaseProvider", memory: "MemoryStore"):
        self.provider = provider
        self.memory = memory

    async def run(
        self,
        task: str,
        agents: list,
        mode: Literal["parallel", "sequential", "best_of"] = "sequential",
        context: list[dict] = None,
    ) -> Union[list, "AgentResult"]:
        if not agents:
            from ruflo.agents.base import AgentResult
            return AgentResult(output="No agents available.", success=False, error="empty agent list")

        if mode == "parallel":
            return await self._run_parallel(task, agents, context)
        elif mode == "best_of":
            return await self._run_best_of(task, agents, context)
        else:
            return await self._run_sequential(task, agents, context)

    async def _run_sequential(self, task: str, agents: list, context: list[dict] = None):
        """Try agents in order, stop on first success."""
        last_result = None
        for agent in agents:
            try:
                result = await agent.run(task, context)
                last_result = result
                if result.success:
                    return result
            except Exception as e:
                from ruflo.agents.base import AgentResult
                last_result = AgentResult(
                    output=f"Agent {agent.name} raised an exception: {str(e)}",
                    success=False,
                    error=str(e),
                )
        # Return last result even if all failed
        return last_result

    async def _run_parallel(self, task: str, agents: list, context: list[dict] = None):
        """Run all agents concurrently and return all results as a list."""
        async def _safe_run(agent):
            try:
                return await agent.run(task, context)
            except Exception as e:
                from ruflo.agents.base import AgentResult
                return AgentResult(
                    output=f"Agent {agent.name} error: {str(e)}",
                    success=False,
                    error=str(e),
                )

        results = await asyncio.gather(*[_safe_run(a) for a in agents])
        return list(results)

    async def _run_best_of(self, task: str, agents: list, context: list[dict] = None):
        """Run top 2 agents in parallel, LLM picks the better one."""
        top_agents = agents[:2]

        if len(top_agents) == 1:
            return await self._run_sequential(task, top_agents, context)

        results = await asyncio.gather(
            *[self._safe_run_agent(a, task, context) for a in top_agents]
        )

        result_a, result_b = results[0], results[1]

        # If one failed, return the other
        if not result_a.success and result_b.success:
            return result_b
        if result_a.success and not result_b.success:
            return result_a
        if not result_a.success and not result_b.success:
            return result_a

        # Both succeeded — ask LLM to pick
        try:
            prompt = _BEST_OF_PROMPT.format(
                task=task,
                response_a=result_a.output[:1500],
                response_b=result_b.output[:1500],
            )
            messages = [
                {
                    "role": "system",
                    "content": "You are a quality evaluator. Return only JSON with winner A or B.",
                },
                {"role": "user", "content": prompt},
            ]
            eval_result = await self.provider.complete(messages, max_tokens=200)
            winner = _extract_winner(eval_result.content)
            return result_a if winner == "A" else result_b
        except Exception:
            # Default to A if LLM evaluation fails
            return result_a

    async def _safe_run_agent(self, agent, task: str, context: list[dict] = None):
        try:
            return await agent.run(task, context)
        except Exception as e:
            from ruflo.agents.base import AgentResult
            return AgentResult(
                output=f"Agent {agent.name} error: {str(e)}",
                success=False,
                error=str(e),
            )
