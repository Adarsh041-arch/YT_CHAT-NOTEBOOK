"""YouTube video subtitle extraction and cleaning."""

import re
import os
from typing import Optional, List, Tuple

import requests
import yt_dlp
from yt_dlp.utils import DownloadError

from .config import VideoConfig


class VideoProcessingError(Exception):
    """Custom exception for video processing errors."""

    pass


class PlaylistError(Exception):
    """Custom exception for playlist processing errors."""
    pass


def validate_video_id(video_id: str) -> bool:
    """Validate YouTube video ID format."""
    if not video_id:
        return False
    pattern = r"^[a-zA-Z0-9_-]{11}$"
    return bool(re.match(pattern, video_id))


def extract_playlist_id(url: str) -> Optional[str]:
    """Extract playlist ID from YouTube playlist URL."""
    patterns = [
        r'[?&]list=([a-zA-Z0-9_-]+)',
        r'playlist\?list=([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_playlist_videos(playlist_url: str) -> List[dict]:
    """Get all video IDs and titles from a YouTube playlist."""
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
            'js_runtimes': {'node': {}},
            'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
        
        if not info or 'entries' not in info:
            raise PlaylistError("Could not extract playlist information")
        
        videos = []
        for entry in info['entries']:
            if entry:
                videos.append({
                    'video_id': entry['id'],
                    'title': entry.get('title', 'Unknown'),
                    'duration': entry.get('duration', 0),
                    'url': entry.get('webpage_url', f"https://youtube.com/watch?v={entry['id']}")
                })
        
        return videos
    except Exception as e:
        raise PlaylistError(f"Failed to extract playlist: {str(e)}")


def extract_subtitle_url(video_id: str, max_retries: int = 3) -> tuple[str, str]:
    """
    Extract subtitle URL and language from YouTube video.
    With retry logic for rate limiting.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    last_error = None

    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(VideoConfig.YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
        except DownloadError as e:
            last_error = e
            if attempt < max_retries - 1:
                import time
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                print(f"Attempt {attempt + 1} failed, waiting {wait_time}s...")
                time.sleep(wait_time)
            continue

        if not info:
            raise VideoProcessingError("Could not extract video information")

        subtitles = info.get("requested_subtitles")
        if not subtitles:
            raise VideoProcessingError("No subtitles found for this video")

        lang = next(iter(subtitles))
        subtitle_url = subtitles[lang]["url"]

        return subtitle_url, lang

    raise VideoProcessingError(f"Failed to fetch video after {max_retries} attempts: {last_error}")


def download_subtitle(url: str) -> str:
    """Download subtitle text from URL."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise VideoProcessingError(f"Failed to download subtitles: {e}")


def clean_vtt(vtt_text: str) -> str:
    """Clean VTT subtitle format into plain text with timestamps."""
    lines = vtt_text.split("\n")
    cleaned_lines: list[str] = []

    current_timestamp = ""
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        ts_match = re.match(r"(\d{2}:\d{2}:\d{2})\.\d{3}\s-->", line)
        if ts_match:
            current_timestamp = f"[{ts_match.group(1)}]"
            i += 1
            continue

        if line.startswith("WEBVTT"):
            i += 1
            continue

        if not line:
            i += 1
            continue

        line = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", line)
        line = re.sub(r"</?c>", "", line)

        if re.match(r"^[\d:\.\s\-]+$", line):
            i += 1
            continue

        if current_timestamp and not line.startswith(current_timestamp):
             line = f"{current_timestamp} {line}"

        cleaned_lines.append(line)
        i += 1

    return " ".join(cleaned_lines).strip()


def process_video(video_id: str) -> tuple[str, str]:
    """
    Full pipeline: validate, extract, download, and clean subtitles.

    Returns:
        tuple[str, str]: (cleaned_transcript, language_code)
    """
    if not validate_video_id(video_id):
        raise VideoProcessingError(f"Invalid video ID format: {video_id}")

    subtitle_url, lang = extract_subtitle_url(video_id)
    raw_subtitle = download_subtitle(subtitle_url)
    cleaned = clean_vtt(raw_subtitle)

    if not cleaned:
        raise VideoProcessingError("Subtitle processing resulted in empty text")

    return cleaned, lang
