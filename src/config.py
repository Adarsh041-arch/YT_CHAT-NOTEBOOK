"""Configuration constants for YTChatBot."""

from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent


class VideoConfig:
    """YouTube video processing settings."""

    SUPPORTED_LANGUAGES: Final[list[str]] = ["en", "hi", "en-US", "hi-IN"]
    YDL_OPTIONS: Final[dict] = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "hi"],
        "quiet": True,
    }


class RAGConfig:
    """RAG pipeline settings."""

    CHUNK_SIZE: Final[int] = 1000
    CHUNK_OVERLAP: Final[int] = 200
    TOP_K_RESULTS: Final[int] = 4


class LLMConfig:
    """LLM settings."""

    MODEL: Final[str] = "gemini-2.5-flash"
    EMBEDDING_MODEL: Final[str] = "gemini-embedding-001"
    TEMPERATURE: Final[float] = 0.3


class StreamlitConfig:
    """UI configuration."""

    APP_TITLE: Final[str] = "YouTube Chatbot"
    VIDEO_ID_PLACEHOLDER: Final[str] = "Enter YouTube video ID..."
    QUESTION_PLACEHOLDER: Final[str] = "Ask your question..."


class APIConfig:
    """API configuration."""

    HOST: Final[str] = "0.0.0.0"
    PORT: Final[int] = 8000
    TITLE: Final[str] = "YTChatBot API"
    VERSION: Final[str] = "1.0.0"
