import asyncio
import datetime
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class RufloResult:
    task: str
    agent_used: str
    output: str
    success: bool
    score: float
    tokens_used: int
    latency_ms: float
    mode: str


class Ruflo:
    def __init__(
        self,
        provider: str = "claude",
        db_path: str = "~/.ruflo/memory.db",
    ):
        self._provider_name = provider
        self._db_path = db_path
        self._initialized = False

        # Component references — set during _ensure_initialized
        self.provider = None
        self.memory = None
        self.router = None
        self.swarm = None
        self.learning = None

    async def _ensure_initialized(self):
        if self._initialized:
            return

        from ruflo.providers import get_provider
        from ruflo.memory import MemoryStore
        from ruflo.router import Router
        from ruflo.swarm import Swarm
        from ruflo.learning import LearningLoop
        from ruflo.agents import set_shared_resources

        self.provider = get_provider(self._provider_name)
        self.memory = MemoryStore(self._db_path)
        await self.memory.initialize()

        # Inject shared resources into agents module so get_agent() reuses them
        set_shared_resources(self.provider, self.memory)

        self.router = Router(self.provider, self.memory)
        self.swarm = Swarm(self.provider, self.memory)
        self.learning = LearningLoop(self.provider, self.memory)
        self._initialized = True

    async def run(
        self,
        task: str,
        session_id: Optional[str] = None,
        mode: str = "sequential",
    ) -> RufloResult:
        await self._ensure_initialized()

        if not session_id:
            session_id = datetime.date.today().isoformat()

        start = time.time()

        # Persist user message
        try:
            await self.memory.save_message(session_id, "user", task)
        except Exception:
            pass

        # Route: get ranked agent names
        try:
            agent_names = await self.router.route(task)
        except Exception:
            agent_names = ["researcher", "coder", "writer", "scraper"]

        # Get conversation context
        try:
            context = await self.memory.get_context(session_id, limit=20)
        except Exception:
            context = []

        # Instantiate agents
        from ruflo.agents import get_agent
        agents = []
        for name in agent_names:
            try:
                agents.append(get_agent(name))
            except Exception:
                pass

        if not agents:
            return RufloResult(
                task=task,
                agent_used="none",
                output="No agents could be initialized.",
                success=False,
                score=0.0,
                tokens_used=0,
                latency_ms=0.0,
                mode=mode,
            )

        # Run through swarm
        try:
            swarm_result = await self.swarm.run(task, agents, mode=mode, context=context)
        except Exception as e:
            from ruflo.agents.base import AgentResult
            swarm_result = AgentResult(
                output=f"Swarm execution failed: {str(e)}",
                success=False,
                error=str(e),
            )

        latency_ms = (time.time() - start) * 1000

        # Determine best result and agent used
        if isinstance(swarm_result, list):
            # Parallel mode returns list
            best = None
            agent_used = agent_names[0] if agent_names else "unknown"
            for i, result in enumerate(swarm_result):
                if result and result.success:
                    best = result
                    agent_used = agent_names[i] if i < len(agent_names) else "unknown"
                    break
            if best is None and swarm_result:
                best = swarm_result[0]
                agent_used = agent_names[0] if agent_names else "unknown"
        else:
            best = swarm_result
            # For sequential/best_of, try to infer which agent succeeded
            agent_used = agent_names[0] if agent_names else "unknown"
            if best and best.success:
                # Match output to agent by checking which one produced it
                for i, agent in enumerate(agents):
                    # We use the primary (first) agent name for sequential
                    pass

        if best is None:
            from ruflo.agents.base import AgentResult
            best = AgentResult(output="No result produced.", success=False)
            agent_used = "unknown"

        # Learning loop — record result and score
        try:
            await self.learning.record(task, agent_used, best, latency_ms)
        except Exception:
            pass

        # Score the result
        try:
            score = await self.learning.score_result(task, best)
        except Exception:
            score = 5.0 if best.success else 1.0

        # Persist assistant response
        try:
            if best.output:
                await self.memory.save_message(session_id, "assistant", best.output)
        except Exception:
            pass

        return RufloResult(
            task=task,
            agent_used=agent_used,
            output=best.output if best.output else "No output.",
            success=best.success,
            score=score,
            tokens_used=best.tokens_used if best else 0,
            latency_ms=latency_ms,
            mode=mode,
        )

    async def chat(self, message: str, session_id: str) -> str:
        result = await self.run(message, session_id=session_id)
        return result.output

    async def get_stats(self) -> list[dict]:
        await self._ensure_initialized()
        return await self.learning.get_stats()

    async def get_memory(self, session_id: str, limit: int = 20) -> list[dict]:
        await self._ensure_initialized()
        return await self.memory.get_context(session_id, limit=limit)

    async def close(self):
        if self.memory:
            await self.memory.close()
