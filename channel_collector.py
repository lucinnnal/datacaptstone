#!/usr/bin/env python3
"""
YouTube Channel Video Collector
Given a list of YouTube channel URLs, fetches the latest N videos per channel
and collects transcript + comments data for each video.
"""

import json
import os
import sys
import argparse
from datetime import datetime

def _is_valid_video_id(video_id):
    """Check if a string looks like a valid YouTube video ID (11 chars, alphanumeric + _ -)."""
    import re
    return bool(re.fullmatch(r'[a-zA-Z0-9_-]{11}', video_id))


def get_channel_videos(channel_url, max_videos=10):
    """
    Use yt-dlp to fetch the latest videos from a YouTube channel.
    Appends /videos to the channel URL to target only regular uploads (skip Shorts/playlists).
    Returns a list of dicts with video url, title, upload_date, etc.
    """
    import yt_dlp

    # Ensure we're targeting the /videos tab to avoid Shorts and playlists
    clean_url = channel_url.rstrip('/')
    if not clean_url.endswith('/videos'):
        clean_url += '/videos'

    # Request more entries than needed so we can filter out non-video items
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlistend': max_videos * 3,
        'nocheckcertificate': True,
    }

    videos = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)

            if info is None:
                print(f"  Warning: Could not extract info from {clean_url}")
                return []

            entries = info.get('entries', [])
            if entries is None:
                entries = []

            for entry in entries:
                if entry is None:
                    continue
                video_id = entry.get('id') or entry.get('url')
                if not video_id:
                    continue

                # Skip non-video entries (channel IDs, playlist IDs, etc.)
                if not _is_valid_video_id(video_id):
                    continue

                video_url = f"https://www.youtube.com/watch?v={video_id}"

                videos.append({
                    'url': video_url,
                    'title': entry.get('title', ''),
                    'upload_date': entry.get('upload_date', ''),
                })

                if len(videos) >= max_videos:
                    break

    except Exception as e:
        print(f"  Error fetching channel videos: {e}")

    return videos


def load_channels(jsonl_file):
    """
    Load channel entries from a JSONL file.
    Each line should be JSON with at least a 'channel_url' field.
    Alternatively, 'url' or 'channel' fields are also accepted.
    """
    channels = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                url = (
                    data.get('channel_url')
                    or data.get('url')
                    or data.get('channel')
                )
                if url:
                    channels.append({
                        'channel_url': url,
                        'channel_name': data.get('channel_name', data.get('name', '')),
                        'line': line_num,
                    })
                else:
                    print(f"Warning: No channel URL found in line {line_num}")
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON at line {line_num}: {e}")
    return channels


def main():
    parser = argparse.ArgumentParser(
        description="Collect YouTube data from a list of channels"
    )
    parser.add_argument("channels_file", help="Input JSONL file with channel URLs")
    parser.add_argument("--output-dir", "-o", default="output_dir",
                        help="Output directory (default: output_dir)")
    parser.add_argument("--videos-per-channel", "-n", type=int, default=10,
                        help="Number of latest videos to collect per channel (default: 10)")
    parser.add_argument("--max-comments", "-m", type=int, default=50,
                        help="Max regular comments per video (default: 50)")
    parser.add_argument("--sort-by", "-s", type=int, choices=[0, 1], default=0,
                        help="Sort comments: 0=Popular, 1=Recent (default: 0)")

    args = parser.parse_args()

    print("=" * 60)
    print("YouTube Channel Data Collector")
    print("=" * 60)
    print(f"Channels file : {args.channels_file}")
    print(f"Output dir    : {args.output_dir}")
    print(f"Videos/channel: {args.videos_per_channel}")
    print(f"Max comments  : {args.max_comments}")
    print(f"Sort by       : {'Popular' if args.sort_by == 0 else 'Recent'}")
    print(f"Started at    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    channels = load_channels(args.channels_file)
    if not channels:
        print("No channels found in the input file.")
        sys.exit(1)

    print(f"Found {len(channels)} channel(s) to process\n")

    os.makedirs(args.output_dir, exist_ok=True)

    # Phase 1: Fetch video URLs from each channel
    print("-" * 60)
    print("Phase 1: Fetching video URLs from channels")
    print("-" * 60)

    all_videos = []  # list of (channel_name, video_info)
    urls_file = os.path.join(args.output_dir, "urls.jsonl")

    with open(urls_file, 'w', encoding='utf-8') as f:
        for idx, ch in enumerate(channels, 1):
            channel_url = ch['channel_url']
            channel_name = ch.get('channel_name', f'channel_{idx}')

            print(f"\n[{idx}/{len(channels)}] {channel_name}: {channel_url}")
            videos = get_channel_videos(channel_url, max_videos=args.videos_per_channel)
            print(f"  Found {len(videos)} video(s)")

            for v in videos:
                entry = {
                    'url': v['url'],
                    'title': v.get('title', ''),
                    'channel_name': channel_name,
                    'channel_url': channel_url,
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                all_videos.append(entry)

    print(f"\nTotal videos to collect: {len(all_videos)}")
    print(f"Video URLs saved to: {urls_file}\n")

    if not all_videos:
        print("No videos found. Exiting.")
        sys.exit(1)

    # Phase 2: Collect transcript + comments for each video
    print("-" * 60)
    print("Phase 2: Collecting transcripts and comments")
    print("-" * 60)

    import youtube_collector

    combined_output = os.path.join(args.output_dir, "combined_data.jsonl")
    success_count = 0
    fail_count = 0

    with open(combined_output, 'w', encoding='utf-8') as f_out:
        for idx, entry in enumerate(all_videos, 1):
            url = entry['url']
            ch_name = entry.get('channel_name', '')
            title = entry.get('title', '')

            print(f"\n[{idx}/{len(all_videos)}] ({ch_name}) {title}")
            print(f"  URL: {url}")

            try:
                data = youtube_collector.collect_video_data(
                    video_url=url,
                    max_regular=args.max_comments,
                    max_timestamp=50,
                    sort_by=args.sort_by,
                )
                # Attach channel info
                data['channel_name'] = ch_name
                data['channel_url'] = entry.get('channel_url', '')
                data['title'] = title

                f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
                f_out.flush()

                if data.get('success'):
                    tc = len(data.get('timestamp_comments', []))
                    rc = len(data.get('regular_comments', []))
                    tr = len(data.get('transcript', []))
                    print(f"  -> transcript: {tr}, timestamp comments: {tc}, regular comments: {rc}")
                    success_count += 1
                else:
                    print("  -> Failed to collect complete data")
                    fail_count += 1

            except Exception as e:
                print(f"  -> Error: {e}")
                fail_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("COLLECTION COMPLETE")
    print("=" * 60)
    print(f"Channels processed : {len(channels)}")
    print(f"Videos processed   : {success_count + fail_count}")
    print(f"  Successful       : {success_count}")
    print(f"  Failed           : {fail_count}")
    print(f"\nOutput files in '{args.output_dir}/':")
    print(f"  - urls.jsonl              (video URL list)")
    print(f"  - combined_data.jsonl     (raw collected data)")

    # Save run log
    log_file = os.path.join(args.output_dir, 'collection_log.json')
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'channels_file': args.channels_file,
            'channels_count': len(channels),
            'videos_per_channel': args.videos_per_channel,
            'total_videos': success_count + fail_count,
            'successful': success_count,
            'failed': fail_count,
        }, f, ensure_ascii=False, indent=2)
    print(f"  - collection_log.json     (run summary)")
    print(f"\nFinished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
