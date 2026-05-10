"""YouTube video subtitle extraction using youtube-transcript-api."""

import re
from typing import Optional, List
from youtube_transcript_api import YouTubeTranscriptApi

from .config import VideoConfig


class VideoProcessingError(Exception):
    pass


class PlaylistError(Exception):
    pass


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
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        transcript = transcript_list.find_transcript(['en', 'hi', 'en-US', 'hi-IN'])
        
        if not transcript:
            fetched = transcript_list.find_generated_transcript(['en', 'hi'])
            if not fetched:
                raise VideoProcessingError("No transcript available")
            transcript = fetched[0]
        
        transcript_data = transcript.fetch()
        lang = transcript.language_code
        
        items = []
        for item in transcript_data:
            items.append({
                "text": item["text"],
                "start": item.get("start"),
                "duration": item.get("duration")
            })
        
        return items, lang
        
    except Exception as e:
        error_msg = str(e)
        if "video_unavailable" in error_msg.lower():
            raise VideoProcessingError("Video unavailable")
        if "transcript" in error_msg.lower() and "disabled" in error_msg.lower():
            raise VideoProcessingError("Transcripts disabled for this video")
        if "no transcript" in error_msg.lower():
            raise VideoProcessingError("No transcript available for this video")
        if "429" in error_msg or "rate" in error_msg.lower():
            raise VideoProcessingError("Rate limited - try again later")
        raise VideoProcessingError(f"Failed to fetch transcript: {error_msg}")


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