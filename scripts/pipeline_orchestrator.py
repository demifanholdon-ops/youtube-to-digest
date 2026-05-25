#!/usr/bin/env python3
"""
Pipeline orchestrator — the main entry point.
Wires together rotation, fetching, article generation, filtering, and distribution.

Usage:
    python pipeline_orchestrator.py --run-once     # Run one cycle
    python pipeline_orchestrator.py --status        # Show rotation status
    python pipeline_orchestrator.py --run-once --channel @Fireship  # Bypass rotation
"""

import os
import sys
import argparse
from datetime import datetime

from .config_loader import load_config, Config
from .youtube_fetcher import YouTubeFetcher
from .transcript_fetcher import TranscriptFetcher
from .article_generator import ArticleGenerator
from .content_filter import ContentFilter
from .rotation_engine import RotationEngine
from .video_tracker import VideoTracker
from .llm_backends import create_backend
from .distributors import create_distributors
from .distributors.base import Article


def find_skill_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_pipeline(config: Config, bypass_channel: str = None):
    """Run one cycle of the pipeline: pick → fetch → filter → generate → distribute."""
    skill_dir = find_skill_dir()
    data_dir = os.path.join(skill_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # Initialize components
    fetcher = YouTubeFetcher()
    transcript_fetcher = TranscriptFetcher()
    backend = create_backend(config.llm_backend, config.llm_model)
    generator = ArticleGenerator(backend, language=config.content.language)
    filter_ = ContentFilter(config.smart_filter, generator)
    tracker = VideoTracker(data_dir)
    rotation = RotationEngine(config.channels, config.frequency, data_dir)

    # Pick next video
    if bypass_channel:
        # Bypass rotation: process a specific channel
        from .config_loader import Channel
        channel = Channel(handle=bypass_channel, name=bypass_channel, channel_id="")
        print(f"[pipeline] Bypassing rotation, using channel: {bypass_channel}")
    else:
        result = rotation.pick_next_video(fetcher)
        if result is None:
            print("[pipeline] No new video to process this cycle.")
            return
        channel, video = result

    # For bypass mode, fetch directly
    if bypass_channel:
        info = fetcher.resolve_channel(bypass_channel)
        if info is None:
            print(f"[pipeline] Could not resolve channel: {bypass_channel}")
            return
        channel = channel  # already a Channel
        # We need to import the right type
        from .config_loader import Channel as Ch
        channel = Ch(handle=bypass_channel, name=info.name, channel_id=info.channel_id)
        video = fetcher.get_latest_new_video(info, tracker.get_processed_ids())
        if video is None:
            print(f"[pipeline] No new video from {bypass_channel}")
            return

    print(f"\n{'=' * 60}")
    print(f"  Selected: {video.title[:60]}")
    print(f"  Channel:  {video.channel_name}")
    print(f"  URL:      {video.url}")
    print(f"{'=' * 60}\n")

    # Step 1: Fetch transcript
    print("[pipeline] Fetching transcript...")
    transcript = transcript_fetcher.fetch(video.video_id)
    if not transcript:
        print("[pipeline] No transcript available. Skipping.")
        return
    print(f"  Transcript: {len(transcript.split())} words")

    # Step 2: Smart filter (optional)
    if config.smart_filter.enabled:
        print("[pipeline] Running smart filter...")
        filter_result = filter_.filter(transcript)
        if filter_result and filter_.should_skip(filter_result):
            print(f"  Filtered out! Tags: {filter_result.tags}")
            tracker.mark_processed(video.video_id, video.title, video.channel_name)
            return
        if filter_result:
            print(f"  TL;DR: {filter_result.tl_dr[:120]}...")
            print(f"  Tags: {filter_result.tags}")
        else:
            filter_result = None
    else:
        filter_result = None

    # Step 3: Generate article
    print("[pipeline] Generating article with AI...")
    article_text = generator.generate_article(video, transcript)
    if not article_text:
        print("[pipeline] Failed to generate article.")
        return

    # Check article length
    if config.smart_filter.enabled and filter_.article_too_short(article_text):
        print(f"  Article too short ({len(article_text.split())} words), skipping.")
        return

    print(f"  Article: {len(article_text.split())} words")

    # Step 4: Build article object
    article = Article(
        title=_generate_title(video.title),
        content=article_text,
        video_title=video.title,
        video_url=video.url,
        channel_name=video.channel_name,
        published_date=video.published_at or datetime.now().isoformat(),
        tl_dr=filter_result.tl_dr if filter_result else "",
        tags=filter_result.tags if filter_result else [],
    )

    # Step 5: Distribute
    print(f"[pipeline] Distributing via {[k for k, v in config.distributors.items() if v]}...")
    distributors = create_distributors(config.distributors)
    success_count = 0
    for dist in distributors:
        name = dist.__class__.__name__
        try:
            ok = dist.distribute(article)
            if ok:
                success_count += 1
                print(f"  {name}: OK")
            else:
                print(f"  {name}: FAILED")
        except Exception as e:
            print(f"  {name}: ERROR — {e}")

    # Step 6: Mark as processed (only if at least one distributor succeeded)
    if success_count > 0:
        tracker.mark_processed(video.video_id, video.title, video.channel_name)
        print(f"  [pipeline] Marked as processed.")
    else:
        print(f"  [pipeline] All distributors failed. Video NOT marked as processed (will retry next cycle).")

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"  Cycle complete. {success_count}/{len(distributors)} distributors succeeded.")
    print(f"{'=' * 60}")


def _generate_title(video_title: str) -> str:
    """Generate a headline different from the video title."""
    # Simple default: use video title as-is. The AI generates the actual headline
    # in the article content.
    return video_title


def show_status(config: Config):
    """Show the current rotation status."""
    skill_dir = find_skill_dir()
    data_dir = os.path.join(skill_dir, "data")
    rotation = RotationEngine(config.channels, config.frequency, data_dir)
    tracker = VideoTracker(data_dir)

    status = rotation.get_status()
    print(f"\n{'=' * 50}")
    print(f"  YOUTUBE-DIGEST STATUS")
    print(f"{'=' * 50}")
    for k, v in status.items():
        print(f"  {k}: {v}")
    print(f"  processed_videos: {tracker.get_count()}")
    print(f"  enabled_distributors: {[k for k, v in config.distributors.items() if v]}")
    print(f"  llm: {config.llm_backend} / {config.llm_model}")
    print(f"{'=' * 50}\n")


def main():
    parser = argparse.ArgumentParser(description="youtube-digest pipeline")
    parser.add_argument("--run-once", action="store_true", help="Run one pipeline cycle")
    parser.add_argument("--status", action="store_true", help="Show rotation status")
    parser.add_argument("--channel", type=str, help="Bypass rotation, process a specific @channel")
    args = parser.parse_args()

    config = load_config()

    if args.status:
        show_status(config)
    elif args.run_once:
        run_pipeline(config, bypass_channel=args.channel)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
