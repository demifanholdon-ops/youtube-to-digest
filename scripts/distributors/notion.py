"""
Notion distributor.
Appends articles as pages to a Notion database.

Requires: NOTION_API_KEY, NOTION_DATABASE_ID in .env
"""

import os
import requests
import markdown

from .base import Distributor, Article


class NotionDistributor(Distributor):
    """Distributes articles to a Notion database."""

    NOTION_API = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    def __init__(self):
        self.api_key = os.getenv("NOTION_API_KEY")
        self.database_id = os.getenv("NOTION_DATABASE_ID")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_VERSION,
        }

    def distribute(self, article: Article) -> bool:
        try:
            page_id = self._create_page(article)
            if page_id:
                self._append_content(page_id, article)
                print(f"  [notion] Page created: {page_id}")
                return True
            return False
        except Exception as e:
            print(f"  [notion] Error: {e}")
            return False

    def _create_page(self, article: Article) -> str:
        """Create a page in the Notion database with metadata."""
        properties = {
            "Title": {
                "title": [{"text": {"content": article.title[:100]}}],
            },
            "Channel": {
                "rich_text": [{"text": {"content": article.channel_name}}],
            },
            "URL": {
                "url": article.video_url,
            },
        }

        # Add tags if the database has a Tags multi-select
        if article.tags:
            properties["Tags"] = {
                "multi_select": [{"name": t} for t in article.tags[:10]],
            }

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
        }

        resp = requests.post(
            f"{self.NOTION_API}/pages",
            headers=self._headers(),
            json=payload,
            timeout=15,
        )
        data = resp.json()
        if "id" not in data:
            print(f"  [notion] Failed to create page: {data}")
            return ""
        return data["id"]

    def _append_content(self, page_id: str, article: Article):
        """Append the full article content as child blocks."""
        children = []

        # TL;DR callout
        if article.tl_dr:
            children.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": f"TL;DR: {article.tl_dr}"}}],
                    "icon": {"type": "emoji", "emoji": "📌"},
                },
            })

        # Divider
        children.append({
            "object": "block",
            "type": "divider",
            "divider": {},
        })

        # Article content — split by double newlines into paragraphs
        html = markdown.markdown(article.content)
        # Simple approach: strip HTML tags for plain text blocks
        import re
        text = re.sub(r'<[^>]+>', '', html)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        for para in paragraphs[:50]:  # Limit blocks to avoid API limits
            if len(para) > 2000:
                para = para[:2000]  # Notion text limit
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": para}}],
                },
            })

        # Append children in batches of 100 (Notion limit)
        for i in range(0, len(children), 100):
            batch = children[i:i + 100]
            resp = requests.patch(
                f"{self.NOTION_API}/blocks/{page_id}/children",
                headers=self._headers(),
                json={"children": batch},
                timeout=30,
            )
            data = resp.json()
            if "object" not in data or data.get("object") != "list":
                print(f"  [notion] Failed to append children (batch {i // 100}): {data}")
