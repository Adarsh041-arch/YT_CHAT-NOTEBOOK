"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field


class ProcessVideoRequest(BaseModel):
    """Request to process a YouTube video."""

    video_id: str = Field(
        ..., min_length=11, max_length=11, description="YouTube video ID"
    )


class ProcessVideoResponse(BaseModel):
    """Response after processing a video."""

    video_id: str
    language: str
    message: str
    chunks_created: int


class ChatRequest(BaseModel):
    """Request to chat about a processed video."""

    video_id: str = Field(..., description="YouTube video ID")
    question: str = Field(..., min_length=1, description="Question about the video")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    answer: str
    video_id: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    videos_loaded: int


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str
