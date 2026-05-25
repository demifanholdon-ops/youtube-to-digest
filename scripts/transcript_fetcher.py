"""
Transcript fetcher using the Supadata API.
Refactored from the original get_transcripts.py with retry logic.
"""

import os
import time
import requests
from typing import Optional


class TranscriptFetcher:
    """Fetches YouTube video transcripts via Supadata API."""

    SUPADATA_URL = "https://api.supadata.ai/v1/transcript"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SUPADATA_API_KEY")
        if not self.api_key or self.api_key.startswith("your_"):
            raise RuntimeError("SUPADATA_API_KEY not set in .env")

    def fetch(self, video_id: str, max_retries: int = 3) -> Optional[str]:
        """
        Fetch transcript text for a video.
        Retries with exponential backoff on rate limits.
        Returns plain text or None.
        """
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    self.SUPADATA_URL,
                    params={"url": youtube_url, "text": "true"},
                    headers={"x-api-key": self.api_key},
                    timeout=60,
                )

                if response.status_code == 200:
                    data = response.json()
                    if "content" in data and data["content"]:
                        return data["content"].strip()
                    elif "transcript" in data and data["transcript"]:
                        segments = data["transcript"]
                        if segments:
                            return " ".join(s.get("text", "") for s in segments).strip()
                    return None

                elif response.status_code == 429:
                    wait = 2 ** attempt
                    print(f"  [transcript] Rate limited, retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                elif response.status_code == 404:
                    return None

                else:
                    print(f"  [transcript] API error {response.status_code}: {response.text[:100]}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                    continue

            except requests.exceptions.Timeout:
                print(f"  [transcript] Timeout (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2)
            except Exception as e:
                print(f"  [transcript] Error: {e}")
                return None

        return None
