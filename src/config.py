"""Configuration constants for YTChatBot."""

from pathlib import Path
from typing import Final
from dotenv import load_dotenv

load_dotenv()

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
        "js_runtimes": {"node": {}},
        "extractor_args": {"youtube": {"player_client": ["android", "ios"]}},
    }


class RAGConfig:
    """RAG pipeline settings."""

    CHUNK_SIZE: Final[int] = 300
    CHUNK_OVERLAP: Final[int] = 50
    TOP_K_RESULTS: Final[int] = 2


class LLMConfig:
    """LLM settings."""

    MODEL: Final[str] = "openai/gpt-5.2"
    EMBEDDING_MODEL: Final[str] = "nomic-embed-text:latest"
    TEMPERATURE: Final[float] = 0.7
    TOP_P: Final[float] = 0.9
    MAX_TOKENS: Final[int] = 1024
    OPENROUTER_API_KEY: Final[str] = ""  # Set your API key here
    OPENROUTER_BASE_URL: Final[str] = "https://openrouter.ai/api/v1"


class StreamlitConfig:
    """UI configuration."""

    APP_TITLE: Final[str] = "YouTube Chatbot"
    VIDEO_ID_PLACEHOLDER: Final[str] = "Enter YouTube video ID..."
    QUESTION_PLACEHOLDER: Final[str] = "Ask your question..."


class APIConfig:
    """API configuration."""

    HOST: Final[str] = "0.0.0.0"
    PORT: Final[int] = 8000
    TITLE: Final[str] = "YT ~ NOTEBOOK"
    VERSION: Final[str] = "1.0.0"


class StorageConfig:
    """Storage configuration for DB and Vector Store."""

    DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
    DB_PATH: Final[Path] = DATA_DIR / "ytchatbot.db"
    FAISS_DIR: Final[Path] = DATA_DIR / "faiss_indexes"

    @classmethod
    def ensure_dirs(cls):
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.FAISS_DIR.mkdir(parents=True, exist_ok=True)
