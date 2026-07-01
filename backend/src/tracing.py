"""Centralized tracing setup for YTChatBot using LangSmith @traceable decorator."""

from __future__ import annotations

from typing import Any

from langsmith import traceable as _langsmith_traceable

traceable = _langsmith_traceable


def trace_embedder(embedder: Any) -> Any:
    """Monkey-patch a sentence-transformers embedder's .encode() with @traceable.

    This ensures every call to embedder.encode(...) appears as a LangSmith
    embedding run, nested under its parent trace (e.g. ingestion, retrieval).
    """
    original_encode = embedder.encode

    @traceable(run_type="embedding", name="SentenceTransformer.encode")
    def _traced_encode(sentences: Any, *args: Any, **kwargs: Any) -> Any:
        return original_encode(sentences, *args, **kwargs)

    embedder.encode = _traced_encode
    return embedder
