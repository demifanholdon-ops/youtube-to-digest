"""
Distributor factory and registry.
"""

from typing import Dict, Type, List

from .base import Distributor
from .email_epub import EmailEpubDistributor
from .feishu import FeishuDistributor
from .notion import NotionDistributor
from .rss import RSSDistributor


_DISTRIBUTOR_REGISTRY: Dict[str, Type[Distributor]] = {
    "email": EmailEpubDistributor,
    "feishu": FeishuDistributor,
    "notion": NotionDistributor,
    "rss": RSSDistributor,
}


def create_distributors(enabled: Dict[str, bool]) -> List[Distributor]:
    """Create instances of enabled distributors."""
    result = []
    for name, is_enabled in enabled.items():
        if is_enabled and name in _DISTRIBUTOR_REGISTRY:
            result.append(_DISTRIBUTOR_REGISTRY[name]())
    return result
