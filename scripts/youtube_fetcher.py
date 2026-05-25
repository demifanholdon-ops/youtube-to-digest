"""
YouTube video fetcher using the YouTube Data API v3.
Refactored from the original get_videos.py into a reusable class.
"""

import os
import requests
from dataclasses import dataclass
from typing import List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


@dataclass
class VideoInfo:
    title: str
    video_id: str
    description: str
    channel_name: str
    channel_handle: str
    url: str
    published_at: str = ""


@dataclass
class ChannelInfo:
    handle: str
    name: str
    channel_id: str
    uploads_playlist_id: str


class YouTubeFetcher:
    """Fetches video data from YouTube channels."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise RuntimeError("YOUTUBE_API_KEY not set in .env")
        self.youtube = build("youtube", "v3", developerKey=self.api_key)

    def resolve_channel(self, handle: str) -> Optional[ChannelInfo]:
        """Resolve a @handle to channel info including uploads playlist ID."""
        clean_handle = handle.lstrip("@")
        try:
            request = self.youtube.channels().list(
                part="snippet,contentDetails",
                forHandle=clean_handle,
            )
            response = request.execute()
            if response.get("items"):
                ch = response["items"][0]
                return ChannelInfo(
                    handle=handle if handle.startswith("@") else f"@{handle}",
                    name=ch["snippet"]["title"],
                    channel_id=ch["id"],
                    uploads_playlist_id=ch["contentDetails"]["relatedPlaylists"]["uploads"],
                )
        except HttpError as e:
            print(f"  [youtube] Error resolving {handle}: {e}")
        return None

    @staticmethod
    def is_short(video_id: str) -> bool:
        """Check if a video is a YouTube Short by testing the /shorts/ URL."""
        shorts_url = f"https://www.youtube.com/shorts/{video_id}"
        try:
            resp = requests.head(shorts_url, allow_redirects=True, timeout=5)
            return "/shorts/" in resp.url
        except Exception:
            return False

    def get_recent_videos(self, channel: ChannelInfo, max_results: int = 10) -> List[VideoInfo]:
        """Get recent long-form videos from a channel's uploads playlist."""
        try:
            request = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=channel.uploads_playlist_id,
                maxResults=max_results,
            )
            response = request.execute()
        except HttpError as e:
            print(f"  [youtube] Error fetching videos for {channel.handle}: {e}")
            return []

        videos = []
        for item in response.get("items", []):
            video_id = item["snippet"]["resourceId"]["videoId"]
            if self.is_short(video_id):
                continue
            videos.append(VideoInfo(
                title=item["snippet"]["title"],
                video_id=video_id,
                description=item["snippet"]["description"],
                channel_name=channel.name,
                channel_handle=channel.handle,
                url=f"https://www.youtube.com/watch?v={video_id}",
                published_at=item["snippet"].get("publishedAt", ""),
            ))
        return videos

    def get_latest_new_video(self, channel: ChannelInfo,
                             processed_ids: set) -> Optional[VideoInfo]:
        """Get the most recent unprocessed long-form video from a channel."""
        videos = self.get_recent_videos(channel, max_results=10)
        for video in videos:
            if video.video_id not in processed_ids:
                return video
        return None
