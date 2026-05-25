"""
Abstract base class for LLM backends.
Each backend (Anthropic, DeepSeek, OpenAI, Ollama) implements this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class FilterResult:
    """Result of the lightweight filter pass (TL;DR + topic classification)."""
    tl_dr: str = ""
    tags: List[str] = field(default_factory=list)
    should_skip: bool = False


class LLMBackend(ABC):
    """Abstract backend for AI article generation."""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str,
                 max_tokens: int = 8000) -> str:
        """Generate a full article from a transcript. Returns markdown text."""
        ...

    @abstractmethod
    def generate_filter(self, system_prompt: str, user_prompt: str,
                        max_tokens: int = 300) -> str:
        """
        Quick pass for smart filtering: TL;DR + topic tags.
        Returns raw text that the content_filter parses.
        """
        ...
