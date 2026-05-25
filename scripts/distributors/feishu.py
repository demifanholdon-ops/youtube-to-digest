"""
Feishu (飞书) distributor.
Creates a Feishu Doc with the full article content,
then sends a message card via bot webhook with TL;DR and link.

Requires: FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_PARENT_FOLDER_TOKEN,
          FEISHU_BOT_WEBHOOK in .env
"""

import os
import time
import requests
import markdown

from .base import Distributor, Article


class FeishuDistributor(Distributor):
    """Distributes articles to Feishu as Docs + message cards."""

    FEISHU_API = "https://open.feishu.cn/open-apis"

    def __init__(self):
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
        self.folder_token = os.getenv("FEISHU_PARENT_FOLDER_TOKEN")
        self.webhook = os.getenv("FEISHU_BOT_WEBHOOK")
        self._token = None
        self._token_expiry = 0

    def _get_token(self) -> str:
        """Get tenant access token, caching until expiry."""
        now = time.time()
        if self._token and now < self._token_expiry:
            return self._token

        resp = requests.post(
            f"{self.FEISHU_API}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu auth failed: {data}")

        self._token = data["tenant_access_token"]
        self._token_expiry = now + data.get("expire", 7200) - 300
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def distribute(self, article: Article) -> bool:
        try:
            doc_url = self._create_doc(article)
            if not doc_url:
                return False
            self._send_message_card(article, doc_url)
            return True
        except Exception as e:
            print(f"  [feishu] Error: {e}")
            return False

    def _create_doc(self, article: Article) -> str:
        """Create a Feishu Doc and write the article content into it."""
        # Step 1: Create the doc
        title = article.title[:100]  # Feishu doc title max 100 chars
        resp = requests.post(
            f"{self.FEISHU_API}/docx/v1/documents",
            headers=self._headers(),
            json={"title": title, "folder_token": self.folder_token},
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 0:
            print(f"  [feishu] Failed to create doc: {data}")
            return ""

        doc_id = data["data"]["document"]["document_id"]
        doc_url = data["data"]["document"]["url"]

        # Step 2: Convert markdown to Feishu doc blocks and write
        blocks = self._markdown_to_blocks(article)
        self._write_blocks(doc_id, blocks)

        print(f"  [feishu] Doc created: {doc_url}")
        return doc_url

    def _markdown_to_blocks(self, article: Article) -> list:
        """Convert article markdown to Feishu doc block structure."""
        blocks = []

        # Header block with channel info
        blocks.append({
            "block_type": 2,  # Text
            "text": {
                "elements": [
                    {"text_run": {"content": f"来源：{article.channel_name} · {article.video_title}\n"}},
                ],
                "style": {"link": {"url": article.video_url}},
            },
        })

        # TL;DR block (if present)
        if article.tl_dr:
            blocks.append({
                "block_type": 2,
                "text": {
                    "elements": [{"text_run": {"content": f"TL;DR: {article.tl_dr}"}}],
                },
            })

        # Tags block
        if article.tags:
            blocks.append({
                "block_type": 2,
                "text": {
                    "elements": [{"text_run": {"content": f"标签：{', '.join(article.tags)}"}}],
                },
            })

        # Divider
        blocks.append({"block_type": 27})

        # Convert markdown content to blocks
        for line in article.content.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("# "):
                blocks.append({
                    "block_type": 3,  # Heading 1
                    "heading1": {
                        "elements": [{"text_run": {"content": stripped[2:]}}],
                    },
                })
            elif stripped.startswith("## "):
                blocks.append({
                    "block_type": 4,  # Heading 2
                    "heading2": {
                        "elements": [{"text_run": {"content": stripped[3:]}}],
                    },
                })
            elif stripped.startswith("### "):
                blocks.append({
                    "block_type": 5,  # Heading 3
                    "heading3": {
                        "elements": [{"text_run": {"content": stripped[4:]}}],
                    },
                })
            else:
                # Plain text (strip markdown bold/italic for simplicity)
                clean = stripped.replace("**", "").replace("*", "").replace("`", "")
                blocks.append({
                    "block_type": 2,
                    "text": {
                        "elements": [{"text_run": {"content": clean}}],
                    },
                })

        return blocks

    def _write_blocks(self, doc_id: str, blocks: list):
        """Write blocks to a Feishu doc in batches."""
        # Get the root block (page) ID
        resp = requests.get(
            f"{self.FEISHU_API}/docx/v1/documents/{doc_id}/blocks",
            headers=self._headers(),
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            print(f"  [feishu] Failed to get doc blocks: {data}")
            return

        page_block_id = data["data"]["items"][0]["block_id"]

        # Write blocks in batches of 50 (Feishu API limit)
        batch_size = 50
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i + batch_size]
            children = [{
                "block_type": b["block_type"],
                **{k: v for k, v in b.items() if k != "block_type"},
            } for b in batch]

            resp = requests.patch(
                f"{self.FEISHU_API}/docx/v1/documents/{doc_id}/blocks/{page_block_id}/children/batch_create",
                headers=self._headers(),
                json={"children": children, "index": -1},
                timeout=30,
            )
            data = resp.json()
            if data.get("code") != 0:
                print(f"  [feishu] Failed to write blocks (batch {i // batch_size}): {data}")

    def _send_message_card(self, article: Article, doc_url: str):
        """Send a Feishu message card with summary and doc link."""
        if not self.webhook:
            print("  [feishu] No bot webhook configured, skipping message card.")
            return

        tag_text = " · ".join(article.tags[:3]) if article.tags else "YouTube Digest"
        tl_dr_text = article.tl_dr[:200] if article.tl_dr else "点击查看完整文章"

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"新文章：{article.title[:60]}"},
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": f"**来源：**{article.channel_name} — {article.video_title}\n\n{tl_dr_text}"},
                    },
                    {"tag": "hr"},
                    {
                        "tag": "note",
                        "elements": [
                            {"tag": "plain_text", "content": tag_text},
                        ],
                    },
                ],
                "config": {
                    "forwardable": True,
                },
            },
        }

        resp = requests.post(
            self.webhook,
            json=card,
            timeout=10,
        )
        data = resp.json()
        if data.get("code") == 0 or data.get("StatusCode") == 0:
            print(f"  [feishu] Message card sent.")
        else:
            print(f"  [feishu] Message card failed: {data}")
