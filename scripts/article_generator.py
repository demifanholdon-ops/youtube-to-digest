"""
Article generator using pluggable LLM backends.
Refactored from the original write_articles.py.
"""

import os
from typing import Optional

from .config_loader import Config
from .llm_backends import create_backend
from .llm_backends.base import LLMBackend
from .youtube_fetcher import VideoInfo


def _load_prompt(name: str, language: str = "zh") -> str:
    """Load a prompt template from references/prompts.md or use built-in defaults."""
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(skill_dir, "references", "prompts.md")

    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            content = f.read()
        # Simple section extraction: find the named section
        marker = f"## {name}"
        if marker in content:
            start = content.index(marker) + len(marker)
            # Find next ## section
            next_marker = content.find("\n## ", start)
            if next_marker == -1:
                section = content[start:]
            else:
                section = content[start:next_marker]
            return section.strip()

    # Built-in fallback for article_writer
    lang_instruction = {
        "zh": "Write the article in Chinese (Simplified).",
        "en": "Write the article in English.",
        "auto": "Write the article in the same language as the transcript.",
    }
    lang_line = lang_instruction.get(language, lang_instruction["zh"])

    return f"""You are a skilled magazine editor. Transform the following YouTube video transcript into a polished, engaging article.

{lang_line}

Guidelines:
- Start with an engaging headline
- Capture key insights, contrarian viewpoints, memorable anecdotes
- Preserve key quotes (clean up filler words)
- Explain jargon and obscure references
- Write in a magazine style — think The New Yorker or The Atlantic
- Do NOT reference "this video" — write it as a standalone article
- Output in clean Markdown format"""


FILTER_PROMPT = """You are a content classifier. Analyze this YouTube video transcript snippet and return a JSON object with exactly these fields:

{{
  "tl_dr": "3-sentence summary of what this video is about",
  "tags": ["tag1", "tag2", "tag3"],
  "should_skip": false
}}

Rules:
- tl_dr: exactly 2-3 sentences summarizing the main topic and key points
- tags: 2-5 lowercase topic tags (e.g., "ai", "startups", "history", "science")
- should_skip: true only if the content is purely entertainment/gossip/drama with no educational value

Return ONLY the JSON object, no other text."""


class ArticleGenerator:
    """Generates articles from transcripts using a pluggable LLM backend."""

    def __init__(self, backend: LLMBackend, language: str = "zh"):
        self.backend = backend
        self.language = language
        self.article_prompt = _load_prompt("article_writer", language)

    def generate_article(self, video: VideoInfo, transcript: str) -> Optional[str]:
        """Transform a transcript into a magazine-style article."""
        user_prompt = f"""VIDEO TITLE: {video.title}
CHANNEL: {video.channel_name}
VIDEO URL: {video.url}

VIDEO DESCRIPTION:
{video.description}

TRANSCRIPT:
{transcript}

---

Transform the above transcript into a magazine article following the guidelines."""

        try:
            return self.backend.generate(
                system_prompt=self.article_prompt,
                user_prompt=user_prompt,
                max_tokens=8000,
            )
        except Exception as e:
            print(f"  [generator] Error generating article: {e}")
            return None

    def generate_filter_result(self, transcript: str) -> Optional["FilterResult"]:
        """Run the lightweight filter pass: TL;DR + tags + skip check."""
        # Import here to avoid circular import
        from .llm_backends.base import FilterResult
        import json

        # Only use first 5000 chars for filtering (save cost)
        snippet = transcript[:5000]
        user_prompt = f"Transcript snippet:\n\n{snippet}"

        try:
            raw = self.backend.generate_filter(
                system_prompt=FILTER_PROMPT,
                user_prompt=user_prompt,
                max_tokens=300,
            )
            # Try to extract JSON from the response
            raw = raw.strip()
            if raw.startswith("```"):
                # Strip markdown code fences
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            result = json.loads(raw)
            return FilterResult(
                tl_dr=result.get("tl_dr", ""),
                tags=result.get("tags", []),
                should_skip=result.get("should_skip", False),
            )
        except Exception as e:
            print(f"  [filter] Error parsing filter result: {e}")
            return FilterResult()
