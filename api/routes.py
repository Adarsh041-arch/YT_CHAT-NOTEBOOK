"""FastAPI routes for YTChatBot API."""

from fastapi import APIRouter, HTTPException

from src.rag_engine import RAGEngine
from src.video_processor import process_video, VideoProcessingError
from .models import (
    ProcessVideoRequest,
    ProcessVideoResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
)

router = APIRouter()

video_store: dict[str, dict] = {}


@router.post("/process", response_model=ProcessVideoResponse)
async def process_video_endpoint(request: ProcessVideoRequest):
    """
    Process a YouTube video: extract subtitles, create embeddings.
    """
    video_id = request.video_id

    if video_id in video_store:
        return ProcessVideoResponse(
            video_id=video_id,
            language=video_store[video_id]["language"],
            message="Video already processed",
            chunks_created=video_store[video_id]["chunks"],
        )

    try:
        transcript, language = process_video(video_id)

        engine = RAGEngine()
        engine.ingest_transcript(transcript, video_id)

        chunks = len(transcript) // 1000 + 1

        video_store[video_id] = {
            "engine": engine,
            "transcript": transcript,
            "language": language,
            "chunks": chunks,
        }

        return ProcessVideoResponse(
            video_id=video_id,
            language=language,
            message="Video processed successfully",
            chunks_created=chunks,
        )

    except VideoProcessingError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Ask a question about a processed video.
    """
    video_id = request.video_id

    if video_id not in video_store:
        raise HTTPException(
            status_code=404, detail="Video not found. Please process the video first."
        )

    engine = video_store[video_id]["engine"]

    try:
        answer = engine.answer(request.question)

        return ChatResponse(
            answer=answer,
            video_id=video_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {e}")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    """
    return HealthResponse(
        status="healthy",
        videos_loaded=len(video_store),
    )


@router.delete("/videos/{video_id}")
async def delete_video(video_id: str):
    """
    Remove a processed video from memory.
    """
    if video_id in video_store:
        del video_store[video_id]
        return {"message": f"Video {video_id} deleted"}

    raise HTTPException(status_code=404, detail="Video not found")
