"""
Rotation engine: round-robin channel selection with deduplication.
The core algorithm that picks which channel's video to process next.

Strict round-robin: processes channels in order, one per cycle.
If a channel has no new video, it skips to the next (no backfill).
Idempotent within a cycle period (won't double-process if run twice same day).
"""

import os
import json
from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import Optional, Set, List

from .config_loader import Channel
from .youtube_fetcher import YouTubeFetcher, VideoInfo


@dataclass
class RotationState:
    current_index: int = 0
    processed_video_ids: List[str] = None  # list for JSON serialization
    last_run_date: str = ""  # ISO date of last run

    def __post_init__(self):
        if self.processed_video_ids is None:
            self.processed_video_ids = []


class RotationEngine:
    """Manages round-robin channel rotation and picks the next video to process."""

    def __init__(self, channels: List[Channel], frequency: str, data_dir: str):
        self.channels = channels
        self.frequency = frequency
        self.state_path = os.path.join(data_dir, "rotation_state.json")
        self.state = self._load_state()

    def _load_state(self) -> RotationState:
        if os.path.exists(self.state_path):
            with open(self.state_path, "r") as f:
                data = json.load(f)
                return RotationState(
                    current_index=data.get("current_index", 0),
                    processed_video_ids=data.get("processed_video_ids", []),
                    last_run_date=data.get("last_run_date", ""),
                )
        return RotationState()

    def _save_state(self):
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(asdict(self.state), f, indent=2)
        os.replace(tmp, self.state_path)

    def _current_cycle_key(self) -> str:
        """Return a string key representing the current cycle period.
        Daily → today's date, Weekly → ISO week, Monthly → YYYY-MM."""
        today = date.today()
        if self.frequency == "daily":
            return today.isoformat()
        elif self.frequency == "weekly":
            return f"{today.year}-W{today.isocalendar()[1]:02d}"
        else:  # monthly
            return f"{today.year}-{today.month:02d}"

    def has_run_this_cycle(self) -> bool:
        """Check if the pipeline already ran in the current cycle."""
        return self.state.last_run_date == self._current_cycle_key()

    def pick_next_video(self, fetcher: YouTubeFetcher) -> Optional[tuple]:
        """
        Pick the next video using round-robin rotation.
        Returns (channel, video) or None if no new video available.
        """
        if self.has_run_this_cycle():
            print(f"[rotation] Already ran this {self.frequency} cycle ({self._current_cycle_key()}). Skipping.")
            return None

        if not self.channels:
            print("[rotation] No channels configured.")
            return None

        processed_set = set(self.state.processed_video_ids)
        start_index = self.state.current_index % len(self.channels)

        for attempt in range(len(self.channels)):
            idx = (start_index + attempt) % len(self.channels)
            channel = self.channels[idx]

            # Resolve channel if not yet resolved
            if not channel.channel_id:
                info = fetcher.resolve_channel(channel.handle)
                if info is None:
                    print(f"  [rotation] Could not resolve {channel.handle}, skipping.")
                    self.state.current_index = (idx + 1) % len(self.channels)
                    self._save_state()
                    continue
                # Update channel info (mutate the frozen dataclass by replacing)
                channel = Channel(
                    handle=channel.handle,
                    name=info.name,
                    channel_id=info.channel_id,
                )
                self.channels[idx] = channel

            print(f"  [rotation] Trying {channel.handle} ({channel.name})...")

            resolved = fetcher.resolve_channel(channel.handle)
            if resolved is None:
                print(f"    No channel info, skipping.")
                self.state.current_index = (idx + 1) % len(self.channels)
                self._save_state()
                continue

            video = fetcher.get_latest_new_video(resolved, processed_set)
            if video:
                # Found a new video
                self.state.processed_video_ids.append(video.video_id)
                self.state.current_index = (idx + 1) % len(self.channels)
                self.state.last_run_date = self._current_cycle_key()
                self._save_state()
                return (channel, video)
            else:
                print(f"    No new video from {channel.handle}, moving to next channel.")
                self.state.current_index = (idx + 1) % len(self.channels)
                self._save_state()

        # Exhausted all channels
        print("[rotation] No new videos from any channel.")
        self.state.last_run_date = self._current_cycle_key()
        self._save_state()
        return None

    def get_status(self) -> dict:
        """Return current rotation status for debugging."""
        return {
            "total_channels": len(self.channels),
            "current_index": self.state.current_index,
            "next_channel": self.channels[self.state.current_index % len(self.channels)].handle
                if self.channels else "none",
            "processed_count": len(self.state.processed_video_ids),
            "last_run": self.state.last_run_date,
            "ran_this_cycle": self.has_run_this_cycle(),
            "frequency": self.frequency,
        }
