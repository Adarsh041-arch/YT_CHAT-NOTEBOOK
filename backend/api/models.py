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


class PlaylistLoadResponse(BaseModel):
    playlist_id: str
    total: int
    succeeded: list[str]
    failed: list[dict]
    videos: list[dict]
    relation_graph: dict


class PlaylistQueryRequest(BaseModel):
    playlist_id: str = Field(..., description="YouTube playlist ID")
    question: str = Field(..., min_length=1, description="Question about the playlist")
    session_id: str | None = Field(None, description="Optional chat session ID")


class PlaylistInfo(BaseModel):
    """Summary info for a processed playlist."""
    playlist_id: str
    total_videos: int
    created_at: str


class VisualizationRequest(BaseModel):
    video_id: str
    question: str
    answer: str = ""


# ── Visualization Spec Models ─────────────────────────────────────

class VizChartDataPoint(BaseModel):
    label: str
    value: float

class VizChart(BaseModel):
    type: str = "chart"
    chartType: str  # "bar" | "line" | "scatter" | "pie"
    title: str
    data: list[VizChartDataPoint]
    xLabel: str = ""
    yLabel: str = ""

class VizGraphNode(BaseModel):
    id: str
    label: str

class VizGraphEdge(BaseModel):
    source: str
    target: str
    label: str | None = None

class VizGraph(BaseModel):
    type: str = "graph"
    title: str
    nodes: list[VizGraphNode]
    edges: list[VizGraphEdge]
    layout: str = "force"  # "force" | "tree" | "radial"

class VizSimulationStep(BaseModel):
    description: str
    state: dict = {}

class VizSimulation(BaseModel):
    type: str = "simulation"
    simType: str  # "particles" | "physics" | "algorithm-steps"
    title: str
    params: dict = {}
    steps: list[VizSimulationStep] | None = None

class VizDiagram(BaseModel):
    type: str = "diagram"
    diagramType: str  # "flowchart" | "sequence"
    mermaidSyntax: str

class VizCustom(BaseModel):
    type: str = "custom"
    title: str
    code: str


class LogValidationRequest(BaseModel):
    video_id: str
    query: str
    category: str
    spec: dict
    validation_error: str | None = None


class RegenerateVisualizationRequest(BaseModel):
    video_id: str
    query: str
    category: str
    failed_code: str
    error_message: str



