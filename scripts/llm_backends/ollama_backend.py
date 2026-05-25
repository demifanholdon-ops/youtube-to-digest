"""
Ollama local backend.
OpenAI-compatible since Ollama v0.1.24. No API key needed.
"""

import os
from openai import OpenAI

from .base import LLMBackend


class OllamaBackend(LLMBackend):
    """Backend for locally running Ollama models."""

    def __init__(self, model: str = "llama3.1:8b"):
        super().__init__(model)
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.client = OpenAI(
            base_url=f"{base_url.rstrip('/')}/v1",
            api_key="ollama",  # Ollama ignores the key
        )
        self._validate_model()

    def _validate_model(self):
        """Check if the model is available locally. Warn if not."""
        import requests
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            resp = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                if self.model not in models:
                    print(f"[ollama] Warning: model '{self.model}' not found locally. "
                          f"Available: {', '.join(models[:10])}")
                    print(f"[ollama] Pull it with: ollama pull {self.model}")
        except Exception:
            print("[ollama] Warning: could not reach Ollama server. Is it running?")
            print("[ollama] Start with: ollama serve")

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
