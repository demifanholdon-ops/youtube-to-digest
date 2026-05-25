"""
LLM Backend factory and registry.
Adding a new backend: 1) create file extending LLMBackend, 2) add one line here.
"""

from typing import Dict, Type

from .base import LLMBackend
from .anthropic_backend import AnthropicBackend
from .deepseek_backend import DeepSeekBackend
from .openai_backend import OpenAIBackend
from .ollama_backend import OllamaBackend


_BACKEND_REGISTRY: Dict[str, Type[LLMBackend]] = {
    "anthropic": AnthropicBackend,
    "deepseek": DeepSeekBackend,
    "openai": OpenAIBackend,
    "ollama": OllamaBackend,
}


def create_backend(backend_name: str, model: str) -> LLMBackend:
    """Create an LLM backend instance by name. Raises ValueError if unknown."""
    cls = _BACKEND_REGISTRY.get(backend_name)
    if cls is None:
        raise ValueError(
            f"Unknown LLM backend: '{backend_name}'. "
            f"Available: {', '.join(sorted(_BACKEND_REGISTRY.keys()))}"
        )
    return cls(model=model)
