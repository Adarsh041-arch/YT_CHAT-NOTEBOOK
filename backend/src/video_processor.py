"""YouTube video subtitle extraction using Invidious API."""

import re
import json
import requests
from typing import Optional, List

from .config import VideoConfig


class VideoProcessingError(Exception):
    pass


class PlaylistError(Exception):
    pass


INVIDIOUS_INSTANCES = [
    "https://invidious.snopyta.org",
    "https://invidious.jingl.xyz",
    "https://invidious.kavin.rocks",
]


def get_invidious_url() -> str:
    for instance in INVIDIOUS_INSTANCES:
        try:
            response = requests.get(f"{instance}/api/v1/videos/dQw4w9WgXcQ", params={"fields": "videoId"}, timeout=5)
            if response.status_code == 200:
                return instance
        except Exception:
            continue
    return INVIDIOUS_INSTANCES[0]


def validate_video_id(video_id: str) -> bool:
    if not video_id:
        return False
    pattern = r"^[a-zA-Z0-9_-]{11}$"
    return bool(re.match(pattern, video_id))


def extract_playlist_id(url: str) -> Optional[str]:
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
    import os
    
    api_key = os.environ.get("YOUTUBE_DATA_API_KEY", "")
    if not api_key:
        raise PlaylistError("YouTube Data API key not configured")
    
    playlist_id = extract_playlist_id(playlist_url)
    if not playlist_id:
        raise PlaylistError("Invalid playlist URL")
    
    from googleapiclient.discovery import build
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    try:
        request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50
        )
        response = request.execute()
        
        videos = []
        for item in response.get('items', []):
            snippet = item.get('snippet', {})
            resource_id = snippet.get('resourceId', {})
            video_id = resource_id.get('videoId', '')
            videos.append({
                'video_id': video_id,
                'title': snippet.get('title', 'Unknown'),
                'duration': 0,
                'url': f'https://youtube.com/watch?v={video_id}'
            })
        return videos
    except Exception as e:
        raise PlaylistError(f"Failed to extract playlist: {str(e)}")
    finally:
        youtube.close()


def get_transcript_with_timestamps(video_id: str) -> tuple[List[dict], str]:
    for base_url in INVIDIOUS_INSTANCES:
        try:
            response = requests.get(
                f"{base_url}/api/v1/videos/{video_id}",
                params={"fields": "captions"},
                timeout=30
            )
            
            if response.status_code != 200:
                continue
            
            data = response.json()
            captions_data = data.get("captions", [])
            
            if not captions_data:
                continue
            
            en_caption = None
            for caption in captions_data:
                lang_code = caption.get("languageCode", "")
                if lang_code.startswith("en"):
                    en_caption = caption
                    break
            
            if not en_caption:
                en_caption = captions_data[0]
            
            caption_id = en_caption.get("captionId")
            if not caption_id:
                continue
            
            transcript_response = requests.get(
                f"{base_url}/api/v1/captions/{video_id}",
                params={"caption_id": caption_id},
                timeout=30
            )
            
            if transcript_response.status_code != 200:
                continue
            
            transcript_text = transcript_response.text
            
            items = []
            lines = transcript_text.split('\n')
            current_start = 0
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('WEBVTT') or line.startswith('NOTE'):
                    continue
                
                if ' --> ' in line:
                    parts = line.split(' --> ')
                    start_time = parts[0].strip()
                    text = parts[1].strip() if len(parts) > 1 else ""
                    
                    start_parts = start_time.replace('.', ':').split(':')
                    try:
                        if len(start_parts) >= 3:
                            hours = int(start_parts[0])
                            minutes = int(start_parts[1])
                            seconds = float(start_parts[2])
                            current_start = hours * 3600 + minutes * 60 + seconds
                    except (ValueError, IndexError):
                        continue
                    
                    if text:
                        items.append({
                            "text": text,
                            "start": current_start,
                            "duration": 3.0
                        })
            
            if items:
                lang = en_caption.get("languageCode", "en")
                return items, lang[:2] if len(lang) > 2 else lang
                
        except Exception:
            continue
    
    raise VideoProcessingError("No captions available")


def format_transcript(items: List[dict]) -> str:
    parts = []
    for item in items:
        start = item.get("start")
        if start is not None:
            minutes = int(start // 60)
            seconds = int(start % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            parts.append(f"{timestamp} {item['text']}")
        else:
            parts.append(item["text"])
    return " ".join(parts)


def process_video(video_id: str) -> tuple[str, str]:
    if not validate_video_id(video_id):
        raise VideoProcessingError(f"Invalid video ID format: {video_id}")

    items, lang = get_transcript_with_timestamps(video_id)
    
    if not items:
        raise VideoProcessingError("Subtitle processing resulted in empty text")

    transcript = format_transcript(items)
    
    return transcript, lang