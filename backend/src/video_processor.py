"""YouTube video subtitle extraction with multi-layer fallback."""

from __future__ import annotations

import re
import os
import random
import asyncio
import time
import tempfile
from typing import Optional, List

from .tracing import traceable

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable


class VideoProcessingError(Exception):
    pass


class RateLimitError(VideoProcessingError):
    """Raised when YouTube returns HTTP 429 — retryable."""


class PlaylistError(Exception):
    pass


# ────── Rate Limiter ──────

class TranscriptRateLimiter:
    """Async rate limiter with escalating IP-level cooldown for YouTube transcript requests.
    
    Cooldown doubles each consecutive 429: 90s -> 180s -> 360s.
    Requires 3 consecutive successes to reduce the streak by 1.
    Adds ±10% jitter to cooldown waits to prevent thundering herd.
    """

    def __init__(self, min_interval: float = 6.0, base_cooldown: float = 90.0, max_cooldown: float = 360.0):
        self._min_interval = min_interval
        self._base_cooldown = base_cooldown
        self._max_cooldown = max_cooldown
        self._current_cooldown = base_cooldown
        self._consecutive_429s = 0
        self._success_streak = 0
        self._last_time = 0.0
        self._blocked_until = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            if now < self._blocked_until:
                wait = self._blocked_until - now
                jitter = random.uniform(0, wait * 0.1)
                print(f"[rate-limit] IP blocked — waiting {wait:.0f}s + {jitter:.0f}s jitter")
                await asyncio.sleep(wait + jitter)
            wait = self._min_interval - (now - self._last_time)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_time = time.monotonic()

    def report_429(self):
        self._consecutive_429s += 1
        self._success_streak = 0
        self._current_cooldown = min(self._base_cooldown * (2 ** (self._consecutive_429s - 1)), self._max_cooldown)
        now = time.monotonic()
        self._blocked_until = now + self._current_cooldown
        print(f"[rate-limit] 429 #{self._consecutive_429s} — IP blocked for {self._current_cooldown:.0f}s")

    def report_success(self):
        self._success_streak += 1
        if self._success_streak >= 3 and self._consecutive_429s > 0:
            self._consecutive_429s -= 1
            self._success_streak = 0
            mult = 2 ** max(0, self._consecutive_429s - 1)
            self._current_cooldown = max(self._base_cooldown, min(self._base_cooldown * mult, self._max_cooldown))
            print(f"[rate-limit] 3 successes — 429 streak reduced to {self._consecutive_429s}")


rate_limiter = TranscriptRateLimiter()


# ────── Constants ──────
_ENV_INVIDIOUS = os.environ.get("INVIDIOUS_BASE_URL")
INVIDIOUS_INSTANCES = (
    [_ENV_INVIDIOUS]
    if _ENV_INVIDIOUS
    else [
        "https://invidious.snopyta.org",
        "https://invidious.jingl.xyz",
        "https://invidious.kavin.rocks",
    ]
)

LANGUAGE_PRIORITY = ["en", "en-US", "hi", "hi-IN", "es"]


# ────── Helpers ──────
def validate_video_id(video_id: str) -> bool:
    if not video_id:
        return False
    pattern = r"^[a-zA-Z0-9_-]{11}$"
    return bool(re.match(pattern, video_id))


def extract_playlist_id(url: str) -> Optional[str]:
    """Extract playlist ID from a YouTube playlist URL."""
    patterns = [
        r'[?&]list=([a-zA-Z0-9_-]+)',
        r'playlist\?list=([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def select_best_caption(captions_data: List[dict]) -> Optional[dict]:
    """Select the best available caption (prefer English)."""
    if not captions_data:
        return None

    for lang in LANGUAGE_PRIORITY:
        for caption in captions_data:
            if caption.get("languageCode", "").startswith(lang):
                return caption

    return captions_data[0]  # Fallback to first available


# ────── Spoiler: Helper to safely parse WebVTT lines with timestamp range ' --> ' ──────
def _safe_split(line: str) -> tuple:
    """Safely split a WebVTT cue line into (start_time_str, text). Returns (None, None) if invalid."""
    if ' --> ' in line:
        parts = line.split(' --> ', 1)
        start_time = parts[0].strip()
        text = parts[1].strip() if len(parts) > 1 else ""
        return start_time, text
    return None, None


def _parse_vtt_timestamp(start_time: str) -> float:
    """Parse a WebVTT timestamp string (HH:MM:SS.mmm) into total seconds. Returns -1 on failure."""
    start_parts = start_time.replace('.', ':').split(':')
    try:
        if len(start_parts) >= 3:
            hours = int(start_parts[0])
            minutes = int(start_parts[1])
            seconds = float(start_parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError):
        pass
    return -1


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


# ═══════════════════════════════════════════════════════
#  LAYER 1: youtube_transcript_api
# ═══════════════════════════════════════════════════════

@traceable(run_type="retriever", name="YouTubeTranscriptAPI")
def _get_youtube_api_transcript(video_id: str) -> tuple[List[dict], str]:
    """
    Fetch transcript using youtube_transcript_api.
    Returns (items, language_code).
    Raises VideoProcessingError if transcript is disabled or not found.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None
        # Priority 1: English (manual or auto-generated)
        try:
            transcript = transcript_list.find_transcript(["en", "en-US", "en-GB"])
        except NoTranscriptFound:
            pass

        # Priority 2: Hindi
        if transcript is None:
            try:
                transcript = transcript_list.find_transcript(["hi", "hi-IN"])
            except NoTranscriptFound:
                pass

        # Priority 3: Spanish
        if transcript is None:
            try:
                transcript = transcript_list.find_transcript(["es"])
            except NoTranscriptFound:
                pass

        # Priority 4: Any available transcript
        if transcript is None:
            for t in transcript_list:
                transcript = t
                break

        if transcript is None:
            raise NoTranscriptFound("No transcripts available for this video")

        # Translate to English if translatable and not already English
        if transcript.is_translatable and transcript.language_code[:2] != "en":
            try:
                translated = transcript.translate("en")
                t_fetched = translated.fetch()
                if t_fetched:
                    items = [{
                        "text": item["text"],
                        "start": item["start"],
                        "duration": item.get("duration", 0.0)
                    } for item in t_fetched]
                    if items:
                        return items, "en"
            except Exception:
                pass

        fetched = transcript.fetch()
        items = [{
            "text": item["text"],
            "start": item["start"],
            "duration": item.get("duration", 0.0)
        } for item in fetched]

        if not items:
            raise VideoProcessingError("youtube_transcript_api returned empty transcript")

        lang = transcript.language_code or "en"
        return items, lang[:2] if len(lang) > 2 else lang

    except (TranscriptsDisabled, VideoUnavailable, NoTranscriptFound) as e:
        raise VideoProcessingError(f"youtube_transcript_api failed: {str(e)}")
    except Exception as e:
        raise VideoProcessingError(f"youtube_transcript_api unexpected error: {str(e)}")


# ═══════════════════════════════════════════════════════
#  LAYER 2: yt-dlp
# ═══════════════════════════════════════════════════════

@traceable(run_type="retriever", name="yt-dlp")
def _get_ytdlp_transcript(video_id: str) -> tuple[List[dict], str]:
    """
    Fetch transcript using yt-dlp.
    Returns (items, language_code).
    Raises VideoProcessingError on failure.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        import yt_dlp

        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "vtt",
            "quiet": True,
            "no_warnings": True,
        }
        proxy = os.environ.get("YT_DLP_PROXY")
        if proxy:
            ydl_opts["proxy"] = proxy

        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts["outtmpl"] = os.path.join(tmpdir, "%(id)s-%(ext)s")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise VideoProcessingError("yt-dlp: Failed to extract video info")

                subtitle_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
                if not subtitle_files:
                    raise VideoProcessingError("yt-dlp: No subtitle file generated")

                subtitle_path = os.path.join(tmpdir, subtitle_files[0])
                with open(subtitle_path, "r", encoding="utf-8") as f:
                    vtt_text = f.read()

                items = _parse_vtt(vtt_text)
                if not items:
                    raise VideoProcessingError("yt-dlp: Parsed VTT is empty")

                lang = "en"
                return items, lang

    except VideoProcessingError:
        raise
    except Exception as e:
        msg = str(e)
        if "429" in msg or "Too Many Requests" in msg:
            raise RateLimitError(f"yt-dlp rate limited: {msg[:100]}")
        raise VideoProcessingError(f"yt-dlp failed: {msg[:200]}")


# ═══════════════════════════════════════════════════════
#  LAYER 3: Invidious (fallback of last resort)
# ═══════════════════════════════════════════════════════

@traceable(run_type="retriever", name="Invidious")
def _get_invidious_transcript(video_id: str) -> tuple[List[dict], str]:
    """
    Fetch transcript using public Invidious instances.
    Returns (items, language_code).
    Raises VideoProcessingError on failure.
    """
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

            en_caption = select_best_caption(captions_data)
            if not en_caption:
                continue

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
            items = _parse_vtt(transcript_text)
            if not items:
                continue

            lang = en_caption.get("languageCode", "en")
            return items, lang[:2] if len(lang) > 2 else lang

        except Exception:
            continue

    raise VideoProcessingError("No captions available via Invidious")


def _parse_vtt(vtt_text: str) -> List[dict]:
    """Parse WebVTT subtitle text into a list of transcript items."""
    items = []
    lines = vtt_text.split('\n')
    current_start = 0.0

    for line in lines:
        line = line.strip()
        if not line or line.startswith('WEBVTT') or line.startswith('NOTE'):
            continue

        # We look for the format: "00:00:00.000 --> 00:00:05.000" or just skip cue numbers
        if '-->' in line:
            start_time_str, text = _safe_split(line)
            if start_time_str is not None:
                current_start = _parse_vtt_timestamp(start_time_str)
                # Occasionally, text can be on the next line(s) in strict VVT. 
                # The current Invidious parser assumed the text was on the same line as the arrow, 
                # but for robustness we keep that assumption and only append if text is present.
                if text:
                    items.append({
                        "text": text,
                        "start": current_start,
                        "duration": 3.0
                    })
        else:
            # If the previous line was a cue header and this line is the actual text
            if items and line:
                # Append text to the last item's text (handles multi-line cues)
                items[-1]["text"] += " " + line

    return items


# ═══════════════════════════════════════════════════════
#  MAIN TRANSCRIPT FETCHER (3-Layer Fallback)
# ═══════════════════════════════════════════════════════

@traceable(run_type="retriever", name="get_transcript_with_timestamps")
async def get_transcript_with_timestamps(video_id: str) -> tuple[List[dict], str]:
    """Fetch a YouTube transcript with rate limiting + 429 IP cooldown."""
    await rate_limiter.acquire()

    errors = []

    # Layer 1: youtube_transcript_api
    try:
        result = _get_youtube_api_transcript(video_id)
        rate_limiter.report_success()
        return result
    except VideoProcessingError as e:
        msg = str(e)
        errors.append(msg)
        if "429" in msg or "too many requests" in msg.lower() or "no element found" in msg:
            rate_limiter.report_429()

    # Layer 2: yt-dlp (try once; on 429 skip immediately to Invidious — no retry in same cycle)
    try:
        result = _get_ytdlp_transcript(video_id)
        rate_limiter.report_success()
        return result
    except RateLimitError as e:
        errors.append(str(e))
        rate_limiter.report_429()
    except VideoProcessingError as e:
        errors.append(str(e))

    # Layer 3: Invidious (different backend)
    try:
        result = _get_invidious_transcript(video_id)
        rate_limiter.report_success()
        return result
    except VideoProcessingError as e:
        errors.append(str(e))

    raise VideoProcessingError(
        f"All transcript extraction methods failed for video {video_id}. "
        f"Errors: {errors}"
    )


# ═══════════════════════════════════════════════════════
#  SINGLE VIDEO PROCESSING
# ═══════════════════════════════════════════════════════

@traceable(run_type="chain", name="process_video")
async def process_video(video_id: str) -> tuple[str, str]:
    """Process a single video and return (transcript_string, language_code)."""
    if not validate_video_id(video_id):
        raise VideoProcessingError(f"Invalid video ID format: {video_id}")

    items, lang = await get_transcript_with_timestamps(video_id)

    if not items:
        raise VideoProcessingError("Subtitle processing resulted in empty text")

    transcript = format_transcript(items)
    return transcript, lang


# ═══════════════════════════════════════════════════════
#  PLAYLIST PROCESSING (uses yt-dlp instead of YouTube Data API)
# ═══════════════════════════════════════════════════════

def get_playlist_videos(playlist_url: str) -> List[dict]:
    """
    Extract video metadata from a YouTube playlist URL using yt-dlp.
    Returns a list of dicts with keys: video_id, title, duration, url.

    Note: Each video's transcript is fetched individually by process_video()
    using the 3-layer fallback when actually needed.
    """
    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            if not info or "entries" not in info:
                raise PlaylistError("Failed to extract playlist entries")

            videos = []
            for entry in info["entries"]:
                if not entry:
                    continue
                video_id = entry.get("id")
                if not video_id:
                    continue
                videos.append({
                    "video_id": video_id,
                    "title": entry.get("title", "Unknown"),
                    "duration": entry.get("duration", 0),
                    "url": f"https://youtube.com/watch?v={video_id}",
                })
            return videos

    except PlaylistError:
        raise
    except Exception as e:
        raise PlaylistError(f"Failed to extract playlist video IDs: {str(e)}")