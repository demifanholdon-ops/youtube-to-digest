"""
Content filter: optional pre-processing step before full article generation.
Runs a quick LLM pass to classify topics, generate TL;DR, and check blocklist.
"""

from typing import Optional

from .config_loader import SmartFilterConfig
from .llm_backends.base import LLMBackend, FilterResult
from .article_generator import ArticleGenerator


class ContentFilter:
    """Smart content filtering: TL;DR generation + topic classification + blocklist."""

    def __init__(self, config: SmartFilterConfig, generator: ArticleGenerator):
        self.config = config
        self.generator = generator

    def should_skip(self, result: FilterResult) -> bool:
        """Check if the article should be skipped based on blocklist."""
        if not self.config.enabled:
            return False
        if result.should_skip:
            return True
        result_tags_lower = [t.lower() for t in result.tags]
        for blocked in self.config.blocked_topics:
            if blocked.lower() in result_tags_lower:
                return True
            # Also check if blocked topic appears in any tag as substring
            for tag in result_tags_lower:
                if blocked.lower() in tag:
                    return True
        return False

    def filter(self, transcript: str) -> Optional[FilterResult]:
        """
        Run the filter pass. Returns FilterResult or None if filtering is disabled.
        The caller checks should_skip() on the result.
        """
        if not self.config.enabled:
            return None
        return self.generator.generate_filter_result(transcript)

    def article_too_short(self, article_text: str) -> bool:
        """Check if the generated article is too short (likely low quality)."""
        if not self.config.enabled:
            return False
        word_count = len(article_text.split())
        return word_count < self.config.min_article_length
