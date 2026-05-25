"""
RSS Feed distributor.
Maintains an RSS 2.0 XML file with generated articles.
Falls back to a local file if no web-accessible path is configured.

Requires: RSS_OUTPUT_PATH in .env
"""

import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import format_datetime
from typing import Optional

from .base import Distributor, Article


class RSSDistributor(Distributor):
    """Distributes articles by appending to an RSS 2.0 XML feed."""

    MAX_ITEMS = 50

    def distribute(self, article: Article) -> bool:
        output_path = os.getenv("RSS_OUTPUT_PATH")
        if not output_path:
            print("  [rss] RSS_OUTPUT_PATH not set in .env")
            return False

        feed_title = os.getenv("RSS_FEED_TITLE", "YouTube Digest")
        base_url = os.getenv("RSS_BASE_URL", "")

        try:
            self._append_to_feed(
                path=output_path,
                feed_title=feed_title,
                article=article,
                base_url=base_url,
            )
            print(f"  [rss] Appended to {output_path}")
            return True
        except Exception as e:
            print(f"  [rss] Error: {e}")
            return False

    def _append_to_feed(self, path: str, feed_title: str, article: Article, base_url: str):
        """Append an article to the RSS feed, creating it if needed."""

        # Load or create RSS feed
        if os.path.exists(path):
            tree = ET.parse(path)
            root = tree.getroot()
            channel = root.find("channel")
            if channel is None:
                channel = ET.SubElement(root, "channel")
        else:
            # Create new RSS 2.0 feed
            root = ET.Element("rss", version="2.0")
            channel = ET.SubElement(root, "channel")
            ET.SubElement(channel, "title").text = feed_title
            ET.SubElement(channel, "link").text = base_url or "https://github.com/youtube-to-digest"
            ET.SubElement(channel, "description").text = "AI-generated article digests from YouTube channels"
            ET.SubElement(channel, "lastBuildDate").text = format_datetime(datetime.now())

        # Create new item
        item = ET.Element("item")
        ET.SubElement(item, "title").text = article.title
        ET.SubElement(item, "link").text = article.video_url

        description = f"<p><strong>来源：{article.channel_name}</strong></p>"
        if article.tl_dr:
            description += f"<p><em>{article.tl_dr}</em></p>"
        description += f"<hr/>"
        # Convert markdown to basic HTML for RSS
        html_body = self._md_to_html(article.content)
        description += html_body
        ET.SubElement(item, "description").text = description

        ET.SubElement(item, "pubDate").text = format_datetime(datetime.now())
        ET.SubElement(item, "guid").text = article.video_url
        if article.tags:
            for tag in article.tags[:5]:
                ET.SubElement(item, "category").text = tag

        # Prepend to feed (newest first)
        channel.insert(0, item)

        # Trim old items
        items = channel.findall("item")
        for old_item in items[self.MAX_ITEMS:]:
            channel.remove(old_item)

        # Update build date
        build_date = channel.find("lastBuildDate")
        if build_date is not None:
            build_date.text = format_datetime(datetime.now())

        # Pretty-print XML
        ET.indent(root, space="  ")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tree = ET.ElementTree(root)
        tree.write(path, encoding="utf-8", xml_declaration=True)

    def _md_to_html(self, md_text: str) -> str:
        """Basic markdown-to-HTML conversion without external deps for RSS."""
        html = md_text
        # Headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        # Double newlines to paragraphs
        paragraphs = html.split("\n\n")
        html = "\n".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())
        return html
