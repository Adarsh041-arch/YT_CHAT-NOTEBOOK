"""Configuration constants for YTChatBot."""

import os
from pathlib import Path
from typing import Final
from dotenv import load_dotenv

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class VideoConfig:
    """YouTube video processing settings."""

    SUPPORTED_LANGUAGES: Final[list[str]] = ["en", "hi", "en-US", "hi-IN"]


class RAGConfig:
    """RAG pipeline settings."""

    CHUNK_SIZE: Final[int] = 1000
    CHUNK_OVERLAP: Final[int] = 150
    TOP_K_RESULTS: Final[int] = 4


class LLMConfig:
    """LLM settings."""

    LLM_PROVIDER: Final[str] = os.environ.get("LLM_PROVIDER", "openrouter")

    MODEL: Final[str] = os.environ.get("LLM_MODEL", "openai/gpt-4o-mini")
    EMBEDDING_MODEL: Final[str] = "all-MiniLM-L6-v2"
    TEMPERATURE: Final[float] = float(os.environ.get("LLM_TEMPERATURE", "0.7"))
    TOP_P: Final[float] = float(os.environ.get("LLM_TOP_P", "0.9"))
    MAX_TOKENS: Final[int] = int(os.environ.get("LLM_MAX_TOKENS", "2048"))

    # OpenRouter
    OPENROUTER_API_KEY: Final[str] = os.environ.get("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: Final[str] = "https://openrouter.ai/api/v1"

    # NVIDIA
    NVIDIA_API_KEY: Final[str] = os.environ.get("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL: Final[str] = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: Final[str] = os.environ.get("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")

    # Google Gemini (compatible with OpenAI format)
    GOOGLE_API_KEY: Final[str] = os.environ.get("GOOGLE_API_KEY", "")
    GEMINI_BASE_URL: Final[str] = "https://generativelanguage.googleapis.com/v1beta/openai/"



class StreamlitConfig:
    """UI configuration."""

    APP_TITLE: Final[str] = "YouTube Chatbot"
    VIDEO_ID_PLACEHOLDER: Final[str] = "Enter YouTube video ID..."
    QUESTION_PLACEHOLDER: Final[str] = "Ask your question..."


class VizConfig:
    """Visualization classifier and spec generation settings."""

    CLASSIFIER_MODEL: Final[str] = os.environ.get(
        "CLASSIFIER_MODEL",
        "gemini-2.5-flash" if os.environ.get("LLM_PROVIDER") == "gemini" else "openai/gpt-4o-mini"
    )
    SPEC_GEN_MODEL: Final[str] = os.environ.get(
        "SPEC_GEN_MODEL",
        "gemini-2.5-flash" if os.environ.get("LLM_PROVIDER") == "gemini" else "openai/gpt-4o-mini"
    )
    CLASSIFIER_MAX_TOKENS: Final[int] = 10
    SPEC_GEN_MAX_TOKENS: Final[int] = 4096
    CLASSIFIER_TEMPERATURE: Final[float] = 0.0


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