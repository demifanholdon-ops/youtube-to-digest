"""
Video tracker: dedup tracking for processed videos.
Prevents re-processing the same video. Includes 90-day pruning
to prevent the JSON file from growing unbounded.

IMPORTANT: This only prunes video ID records used for dedup.
Generated articles, EPUBs, and Feishu docs are NEVER auto-deleted.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Set


class VideoTracker:
    """Tracks processed video IDs to avoid duplicates."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.tracker_path = os.path.join(data_dir, "processed_videos.json")
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.tracker_path):
            with open(self.tracker_path, "r") as f:
                return json.load(f)
        return {"videos": {}}

    def _save(self):
        os.makedirs(self.data_dir, exist_ok=True)
        tmp = self.tracker_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self.tracker_path)

    def is_processed(self, video_id: str) -> bool:
        return video_id in self._data.get("videos", {})

    def mark_processed(self, video_id: str, title: str, channel: str):
        self._data.setdefault("videos", {})[video_id] = {
            "title": title,
            "channel": channel,
            "processed_at": datetime.now().isoformat(),
        }
        self._save()

    def get_processed_ids(self) -> Set[str]:
        return set(self._data.get("videos", {}).keys())

    def get_count(self) -> int:
        return len(self._data.get("videos", {}))

    def prune_old(self, max_age_days: int = 90):
        """
        Remove video ID records older than max_age_days.
        This keeps the JSON file small by removing IDs of old videos
        that are extremely unlikely to be re-encountered.

        This does NOT delete articles, EPUBs, or any generated content.
        It only removes dedup tracking entries.
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        videos = self._data.get("videos", {})
        to_remove = []
        for vid, info in videos.items():
            try:
                processed_at = datetime.fromisoformat(info.get("processed_at", ""))
                if processed_at < cutoff:
                    to_remove.append(vid)
            except (ValueError, TypeError):
                pass

        for vid in to_remove:
            del videos[vid]

        if to_remove:
            self._save()
            print(f"[tracker] Pruned {len(to_remove)} old entries (> {max_age_days} days). "
                  f"Articles and generated content are NOT affected.")
