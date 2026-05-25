"""
DeepSeek Chat Completions API backend.
DeepSeek follows the OpenAI-compatible Chat Completions API.
Cost is ~1/20th of Claude.
"""

import os
from openai import OpenAI

from .base import LLMBackend


class DeepSeekBackend(LLMBackend):
    """Backend for DeepSeek models via OpenAI-compatible API."""

    def __init__(self, model: str = "deepseek-chat"):
        super().__init__(model)
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set in .env")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

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
