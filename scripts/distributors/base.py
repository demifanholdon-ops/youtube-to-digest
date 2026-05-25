"""
Distributor abstract base class.
Each distribution channel (Feishu, Notion, Email, RSS) implements this.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class Article:
    """A generated article ready for distribution."""
    title: str
    content: str           # Markdown body
    video_title: str
    video_url: str
    channel_name: str
    published_date: str
    tl_dr: str = ""        # 3-sentence summary
    tags: List[str] = field(default_factory=list)


class Distributor(ABC):
    """Abstract distribution channel. Subclass and implement distribute()."""

    @abstractmethod
    def distribute(self, article: Article) -> bool:
        """Deliver the article. Returns True on success."""
        ...
