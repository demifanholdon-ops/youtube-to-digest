"""
Email + EPUB distributor.
Refactored from the original send_email.py.
Generates EPUB ebooks and sends them via Gmail SMTP.
"""

import os
import json
import shutil
import smtplib
import markdown
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from ebooklib import epub

from .base import Distributor, Article


class EmailEpubDistributor(Distributor):
    """Distributes articles as EPUB ebooks via email."""

    def distribute(self, article: Article) -> bool:
        gmail_address = os.getenv("GMAIL_ADDRESS")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        recipient = os.getenv("EMAIL_RECIPIENT", gmail_address)

        if not all([gmail_address, gmail_password]):
            print("  [email] GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set in .env")
            return False

        # Create EPUB
        epub_path = self._create_epub(article)
        if not epub_path:
            return False

        # Create HTML email body
        html = self._create_html(article)
        text = self._create_text(article)

        # Build and send email
        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = f"YouTube Digest: {article.title[:60]}"
            msg["From"] = gmail_address
            msg["To"] = recipient

            body = MIMEMultipart("alternative")
            body.attach(MIMEText(text, "plain"))
            body.attach(MIMEText(html, "html"))
            msg.attach(body)

            # Attach EPUB
            with open(epub_path, "rb") as f:
                part = MIMEBase("application", "epub+zip")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(epub_path)}",
                )
                msg.attach(part)

            with smtplib.SMTP_SSL(os.getenv("SMTP_SERVER", "smtp.gmail.com"),
                                  int(os.getenv("SMTP_PORT", "465"))) as server:
                server.login(gmail_address, gmail_password)
                server.sendmail(gmail_address, recipient, msg.as_string())

            print(f"  [email] Sent to {recipient}")
            self._archive(html, epub_path, article)
            os.remove(epub_path)
            return True

        except Exception as e:
            print(f"  [email] Failed: {e}")
            return False

    def _create_epub(self, article: Article) -> str:
        """Create an EPUB file from the article."""
        today = datetime.now().strftime("%Y%m%d")
        filepath = os.path.join(os.path.dirname(__file__), f"youtube_digest_{today}.epub")

        book = epub.EpubBook()
        book.set_identifier(f"youtube-digest-{today}")
        book.set_title(article.title[:80])
        book.set_language("en")
        book.add_author("YouTube Digest")

        style = """
        body { font-family: Georgia, serif; line-height: 1.6; padding: 1em; }
        h1 { font-size: 1.5em; border-bottom: 1px solid #ccc; padding-bottom: 0.3em; }
        h2 { font-size: 1.3em; }
        h3 { font-size: 1.1em; }
        .intro { background: #f5f5f5; padding: 1em; border-left: 3px solid #666; margin-bottom: 1.5em; }
        .watch-link { margin-top: 1.5em; padding: 0.5em; background: #f0f0f0; display: block; }
        .tl-dr { background: #fff9e6; padding: 1em; border-left: 3px solid #d4a855; margin-bottom: 1.5em; }
        """
        nav_css = epub.EpubItem(uid="style", file_name="style/nav.css",
                                media_type="text/css", content=style)
        book.add_item(nav_css)

        tl_dr_html = f'<div class="tl-dr"><strong>TL;DR:</strong> {article.tl_dr}</div>' if article.tl_dr else ""
        article_html = markdown.markdown(article.content)

        chapter_content = f"""
        <html><head><link rel="stylesheet" type="text/css" href="style/nav.css"/></head>
        <body>
            <div class="intro"><em>From "<strong>{article.video_title}</strong>" — {article.channel_name}</em></div>
            {tl_dr_html}
            {article_html}
            <p class="watch-link">Original video: {article.video_url}</p>
        </body></html>"""

        chapter = epub.EpubHtml(title=article.title[:50], file_name="article.xhtml", lang="en")
        chapter.content = chapter_content
        chapter.add_item(nav_css)
        book.add_item(chapter)

        book.toc = (chapter,)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav", chapter]

        epub.write_epub(filepath, book)
        print(f"  [email] Created EPUB: {os.path.basename(filepath)}")
        return filepath

    def _create_html(self, article: Article) -> str:
        article_html = markdown.markdown(article.content)
        tl_dr_section = f'<div style="background:#fff9e6;padding:1em;border-left:3px solid #d4a855;margin-bottom:1.5em"><strong>TL;DR:</strong> {article.tl_dr}</div>' if article.tl_dr else ""
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{{font-family:Georgia,serif;font-size:18px;max-width:700px;margin:0 auto;padding:20px;background:#f9f9f9;color:#333}}
.header{{text-align:center;padding:30px 0;border-bottom:3px solid #333;margin-bottom:30px}}
.header h1{{margin:0;font-size:28px}}
.article{{background:white;padding:30px;border-radius:5px;box-shadow:0 2px 5px rgba(0,0,0,0.1)}}
.article-intro{{background:#f8f8f8;padding:15px 20px;border-left:4px solid #666;margin-bottom:25px;font-size:16px;color:#555}}
.article-content{{font-size:18px;line-height:1.9}}
.watch-link{{display:inline-block;margin-top:20px;padding:12px 24px;background:#ff0000;color:white;text-decoration:none;border-radius:5px;font-size:16px}}
.footer{{text-align:center;color:#999;font-size:14px;padding:20px}}
</style></head>
<body>
<div class="header"><h1>YOUTUBE DIGEST</h1><p>{datetime.now().strftime('%B %d, %Y')}</p></div>
<div class="article">
<div class="article-intro"><em>From "<strong>{article.video_title}</strong>" — {article.channel_name}</em></div>
{tl_dr_section}
<div class="article-content">{article_html}</div>
<a href="{article.video_url}" class="watch-link">Watch original video</a>
</div>
<div class="footer">Generated by youtube-digest</div>
</body></html>"""

    def _create_text(self, article: Article) -> str:
        tl_dr = f"\nTL;DR: {article.tl_dr}\n" if article.tl_dr else ""
        return f"""YouTube Digest — {article.title}

From: {article.channel_name}
Original: {article.video_url}
{tl_dr}
{article.content}
"""

    def _archive(self, html: str, epub_path: str, article: Article):
        """Save a local copy of the newsletter."""
        skill_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        archive_dir = os.path.join(skill_dir, "data", "archive")
        os.makedirs(archive_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(os.path.join(archive_dir, f"digest_{ts}.html"), "w") as f:
            f.write(html)
        shutil.copy(epub_path, os.path.join(archive_dir, f"digest_{ts}.epub"))
        with open(os.path.join(archive_dir, f"digest_{ts}.json"), "w") as f:
            json.dump({"title": article.title, "channel": article.channel_name,
                       "date": ts, "tags": article.tags}, f, indent=2)
