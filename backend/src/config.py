"""Configuration constants for YTChatBot."""

import os
from pathlib import Path
from typing import Final
from dotenv import load_dotenv

PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class VideoConfig:
    """YouTube video processing settings."""

    SUPPORTED_LANGUAGES: Final[list[str]] = ["en", "hi", "en-US", "hi-IN"]


class RAGConfig:
    """RAG pipeline settings."""

    CHUNK_SIZE: Final[int] = 500
    CHUNK_OVERLAP: Final[int] = 50
    TOP_K_RESULTS: Final[int] = 2


class LLMConfig:
    """LLM settings."""

    MODEL: Final[str] = "openai/gpt-5.2"
    EMBEDDING_MODEL: Final[str] = "all-MiniLM-L6-v2"
    TEMPERATURE: Final[float] = 0.7
    TOP_P: Final[float] = 0.9
    MAX_TOKENS: Final[int] = 1024
    OPENROUTER_API_KEY: Final[str] = os.environ.get("OPENROUTER_API_KEY", "")
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
    MONGODB_URL: Final[str] = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: Final[str] = os.environ.get("DATABASE_NAME", "ytchatbot")
    PINECONE_API_KEY: Final[str] = os.environ.get("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: Final[str] = os.environ.get("PINECONE_INDEX_NAME", "ytchatbot")

    @classmethod
    def ensure_dirs(cls):
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)