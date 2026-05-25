"""
Anthropic Messages API backend.
Uses the official anthropic SDK.
"""

import os
import anthropic

from .base import LLMBackend


class AnthropicBackend(LLMBackend):
    """Backend for Anthropic Claude models via Messages API."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(self, system_prompt: str, user_prompt: str,
                 max_tokens: int = 8000) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    def generate_filter(self, system_prompt: str, user_prompt: str,
                        max_tokens: int = 300) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
