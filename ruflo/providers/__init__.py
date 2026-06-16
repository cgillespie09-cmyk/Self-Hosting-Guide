from .claude import ClaudeProvider
from .openai import OpenAIProvider

_registry = {"claude": ClaudeProvider, "openai": OpenAIProvider}
_instances: dict = {}


def get_provider(name: str = "claude"):
    if name not in _instances:
        cls = _registry.get(name)
        if not cls:
            raise ValueError(f"Unknown provider: {name}. Choose from: {list(_registry)}")
        _instances[name] = cls()
    return _instances[name]
