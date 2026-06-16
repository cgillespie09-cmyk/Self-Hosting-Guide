from .base import BaseAgent, AgentResult

AGENT_NAMES = ["researcher", "coder", "writer", "scraper"]

# Shared lazy-initialized resources
_memory_store = None
_provider = None
_agent_instances: dict[str, BaseAgent] = {}


def _get_shared_memory():
    global _memory_store
    if _memory_store is None:
        from ruflo.memory import MemoryStore
        _memory_store = MemoryStore("~/.ruflo/memory.db")
    return _memory_store


def _get_shared_provider():
    global _provider
    if _provider is None:
        from ruflo.providers import get_provider
        _provider = get_provider("claude")
    return _provider


def get_agent(name: str) -> BaseAgent:
    global _agent_instances
    if name not in _agent_instances:
        provider = _get_shared_provider()
        memory = _get_shared_memory()

        if name == "researcher":
            from .researcher import ResearcherAgent
            _agent_instances[name] = ResearcherAgent(provider, memory)
        elif name == "coder":
            from .coder import CoderAgent
            _agent_instances[name] = CoderAgent(provider, memory)
        elif name == "writer":
            from .writer import WriterAgent
            _agent_instances[name] = WriterAgent(provider, memory)
        elif name == "scraper":
            from .scraper import ScraperAgent
            _agent_instances[name] = ScraperAgent(provider, memory)
        else:
            raise ValueError(f"Unknown agent: {name}")
    return _agent_instances[name]


def set_shared_resources(provider, memory):
    """Allow core.py to inject already-initialized resources."""
    global _provider, _memory_store
    _provider = provider
    _memory_store = memory
    # Clear cached instances so they pick up new resources
    _agent_instances.clear()


__all__ = ["BaseAgent", "AgentResult", "get_agent", "set_shared_resources", "AGENT_NAMES"]
