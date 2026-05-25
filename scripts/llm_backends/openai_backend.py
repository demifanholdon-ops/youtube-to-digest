"""
OpenAI Chat Completions API backend.
Uses the official openai SDK.
"""

import os
from openai import OpenAI

from .base import LLMBackend


class OpenAIBackend(LLMBackend):
    """Backend for OpenAI models (GPT-4o, etc.) via Chat Completions API."""

    def __init__(self, model: str = "gpt-4o"):
        super().__init__(model)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in .env")
        self.client = OpenAI(api_key=api_key)

    def _call(self, system_prompt: str, user_prompt: str,
              max_tokens: int) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def generate(self, system_prompt: str, user_prompt: str,
                 max_tokens: int = 8000) -> str:
        return self._call(system_prompt, user_prompt, max_tokens)

    def generate_filter(self, system_prompt: str, user_prompt: str,
                        max_tokens: int = 300) -> str:
        return self._call(system_prompt, user_prompt, max_tokens)
