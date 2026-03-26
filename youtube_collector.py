#!/usr/bin/env python3
"""
YouTube Transcript and Comment Collector
Collects transcript and comments (separated by timestamp comments) from a YouTube video.
"""

import json
import re
import sys
import argparse

def parse_timestamp(text):
    """
    Parse timestamp patterns from comment text.
    Supports formats like: 1:23, 12:34, 1:23:45, 0:00, etc.
    """
    timestamp_pattern = r'\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b'
    matches = re.findall(timestamp_pattern, text)
    return matches if matches else None

def get_video_length(video_url):
    """Get video length using yt-dlp."""
    try:
        import yt_dlp
        ydl_opts = {'quiet': True, 'skip_download': True, 'nocheckcertificate': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('duration', 0)
    except Exception as e:
        print(f"Error getting video length: {e}")
        return 0

def get_transcript(video_id):
    """Get transcript from YouTube video."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        # Instantiate the API object (required in some versions)
        api = YouTubeTranscriptApi()
        
        try:
            # Using instance methods
            transcript_list = api.list(video_id)
            transcript = transcript_list.find_transcript(['ko', 'en'])
            return transcript.fetch()
        except Exception:
            # Fallback for static method call if instance fails
            try:
                transcript_list = YouTubeTranscriptApi.list(video_id)
                transcript = transcript_list.find_transcript(['ko', 'en'])
                return transcript.fetch()
            except Exception as e:
                # Last resort: common static call
                if hasattr(YouTubeTranscriptApi, 'get_transcript'):
                    return YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
                else:
                    raise e
                    
    except Exception as e:
        print(f"Error getting transcript: {e}")
        return None

def get_comments(video_url, sort_by=0, max_regular=1000, max_timestamp=100):
    """
    Get comments from YouTube video.
    sort_by: 0 (Popular - 인기순), 1 (Recent - 최신순)
    """
    try:
        from youtube_comment_downloader import YoutubeCommentDownloader
        downloader = YoutubeCommentDownloader()
        
        generator = downloader.get_comments_from_url(video_url, sort_by=sort_by)
        
        timestamp_comments = []
        regular_comments = []
        
        max_scans_limit = 50000
        scanned_count = 0
        
        for comment in generator:
            scanned_count += 1
            if scanned_count > max_scans_limit:
                break
                
            comment_text = comment.get('text', '')
            
            if is_meaningful_comment(comment_text):
                timestamps = parse_timestamp(comment_text)
                
                if timestamps:
                    if len(timestamp_comments) < max_timestamp:
                        timestamp_comments.append({
                            **comment,
                            'timestamps_found': timestamps
                        })
                else:
                    if len(regular_comments) < max_regular:
                        regular_comments.append(comment)
                        
            if len(timestamp_comments) >= max_timestamp and len(regular_comments) >= max_regular:
                break
                
        return timestamp_comments, regular_comments, scanned_count
    except Exception as e:
        print(f"Error getting comments: {e}")
        return None, None, 0

def is_meaningful_comment(text):
    if not text:
        return False
        
    text_clean = re.sub(r'\s+', '', text)
    if len(text_clean) < 10:
        return False
        
    meaningful_chars = len(re.findall(r'[가-힣a-zA-Z0-9]', text))
    if meaningful_chars < 10:
        return False
        
    if meaningful_chars / len(text_clean) < 0.4:
        return False
        
    return True

def extract_video_id(url):
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def collect_video_data(video_url, max_regular=1000, max_timestamp=200, sort_by=0):
    """Collects all required data for a single video."""
    video_id = extract_video_id(video_url)
    if not video_id:
        print(f"Error: Could not extract video ID from {video_url}")
        return {
            'video_url': video_url,
            'success': False,
            'error': 'Invalid video ID'
        }

    print(f"Processing video ID: {video_id}...")
    
    duration = get_video_length(video_url)
    transcript = get_transcript(video_id)
    timestamp_comments, regular_comments, _ = get_comments(
        video_url, sort_by=sort_by, max_regular=max_regular, max_timestamp=max_timestamp
    )

    success = transcript is not None and timestamp_comments is not None and regular_comments is not None
    
    return {
        'video_url': video_url,
        'video_id': video_id,
        'success': success,
        'video_length': duration,
        'transcript': transcript if transcript else [],
        'timestamp_comments': timestamp_comments if timestamp_comments else [],
        'regular_comments': regular_comments if regular_comments else []
    }

def main():
    parser = argparse.ArgumentParser(description="YouTube Data Collector")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--max-comments", "-m", type=int, default=1000, 
                        help="Maximum number of comments to collect (default: 1000)")
    parser.add_argument("--sort-by", "-s", type=int, choices=[0, 1], default=0,
                        help="Sort comments by: 0 for Popular, 1 for Recent (default: 0)")
    parser.add_argument("--output", "-o", default="output.jsonl", help="Output JSONL file")
    
    args = parser.parse_args()
    
    data = collect_video_data(args.url, max_regular=args.max_comments, sort_by=args.sort_by)
    
    with open(args.output, 'a', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')
    
    if data['success']:
        print(f"✓ Data successfully saved to {args.output}")
    else:
        print("✗ Failed to collect complete data")

if __name__ == "__main__":
    main()
