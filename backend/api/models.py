"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field


class ProcessVideoRequest(BaseModel):
    """Request to process a YouTube video."""

    video_id: str = Field(
        ..., min_length=11, description="YouTube video ID (11 chars) or full URL"
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
    session_id: str | None = Field(None, description="Chat session ID")


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


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)

class Token(BaseModel):
    access_token: str
    token_type: str

class SessionInfo(BaseModel):
    id: str
    video_id: str
    title: str
    created_at: str
    message_count: int


class ProcessPlaylistRequest(BaseModel):
    """Request to process a YouTube playlist."""

    playlist_url: str = Field(..., description="YouTube playlist URL or ID")


class PlaylistVideoInfo(BaseModel):
    """Information about a video in a playlist."""

    video_id: str
    title: str
    duration: int
    url: str
    status: str = "pending"
    progress: str | None = None


class ProcessPlaylistResponse(BaseModel):
    """Response after processing a playlist."""

    playlist_id: str
    total_videos: int
    videos: list[PlaylistVideoInfo]
    message: str
