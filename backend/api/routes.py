"""FastAPI routes for YTChatBot API."""

import os
import uuid
import re
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm

from src.rag_engine import RAGEngine, PineconeRetriever
from src.video_processor import process_video, VideoProcessingError, get_playlist_videos, extract_playlist_id, PlaylistError
from src.database import Video, ChatSession, ChatMessage, User
from src.auth import get_password_hash, verify_password, create_access_token, get_current_user
from langchain_core.messages import HumanMessage, AIMessage
from .models import (
    ProcessVideoRequest,
    ProcessVideoResponse,
    ChatRequest,
    HealthResponse,
    UserCreate,
    Token,
    SessionInfo,
    ProcessPlaylistRequest,
    ProcessPlaylistResponse,
    PlaylistVideoInfo
)

router = APIRouter()

engine_store: dict[str, RAGEngine] = {}


def extract_video_id(input_str: str) -> str:
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, input_str)
        if match:
            return match.group(1)
    if len(input_str) >= 11:
        return input_str[:11]
    return input_str


def get_engine(video_id: str) -> RAGEngine:
    if video_id not in engine_store:
        engine = RAGEngine()
        try:
            engine._video_id = video_id
            engine._index = engine._get_pinecone_index()
            
            if engine._namespace_exists(video_id):
                engine._retriever = PineconeRetriever(
                    index=engine._index,
                    embedding_model=engine.embedding_model,
                    video_id=video_id,
                    top_k=2
                )
                engine._build_chain()
                engine_store[video_id] = engine
            else:
                raise RuntimeError(f"Video not processed yet: {video_id}")
        except Exception as e:
            print(f"Warning: Could not load Pinecone index for {video_id}: {e}")
            raise RuntimeError(f"Video not processed. Please process the video first: {e}")
    return engine_store[video_id]


# --- Auth Routes ---

@router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    existing = await User.find_by_username(user_data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user_data.password)
    new_user = await User.create(user_data.username, hashed_password)
    await User.insert(new_user)
    
    access_token = create_access_token(data={"sub": new_user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await User.find_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


# --- Video Routes ---

@router.post("/process", response_model=ProcessVideoResponse)
async def process_video_endpoint(request: ProcessVideoRequest):
    video_id = extract_video_id(request.video_id)
    if len(video_id) != 11:
        raise HTTPException(status_code=400, detail="Invalid YouTube video ID")

    existing_video = await Video.find_by_id(video_id)
    if existing_video:
        return ProcessVideoResponse(
            video_id=video_id,
            language=existing_video["language"],
            message="Video already processed",
            chunks_created=existing_video["chunks_created"],
        )

    try:
        transcript, language = process_video(video_id)
        engine = RAGEngine()
        engine.load_or_ingest_transcript(transcript, video_id)
        engine_store[video_id] = engine
        chunks = len(transcript) // 1000 + 1

        db_video = await Video.create(video_id, language, chunks)
        await Video.insert(db_video)

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


@router.post("/playlist/stream")
async def process_playlist_stream(request: ProcessPlaylistRequest):
    playlist_id = extract_playlist_id(request.playlist_url)
    if not playlist_id:
        raise HTTPException(status_code=400, detail="Invalid playlist URL")

    try:
        videos = get_playlist_videos(request.playlist_url)
    except PlaylistError as e:
        raise HTTPException(status_code=400, detail=str(e))

    video_infos = []
    total = len(videos)

    async def generate():
        import json
        import asyncio
        processed_count = 0

        for idx, video in enumerate(videos):
            vid = video['video_id']
            yield f"data: {json.dumps({'type': 'progress', 'current': idx + 1, 'total': total, 'title': video['title']})}\n\n"

            existing = await Video.find_by_id(vid)
            if existing:
                status = "already_loaded"
            else:
                try:
                    transcript, language = process_video(vid)
                    engine = RAGEngine()
                    engine.load_or_ingest_transcript(transcript, vid)
                    engine_store[vid] = engine
                    chunks = len(transcript) // 500 + 1

                    db_video = await Video.create(vid, language, chunks)
                    await Video.insert(db_video)
                    status = "processed"
                    processed_count += 1
                except Exception as e:
                    status = f"error: {str(e)[:50]}"

            video_info = {
                'video_id': vid,
                'title': video['title'],
                'duration': video.get('duration', 0),
                'url': video['url'],
                'status': status
            }
            video_infos.append(PlaylistVideoInfo(**video_info))
            yield f"data: {json.dumps({'type': 'video_done', 'video': video_info})}\n\n"

            if idx < total - 1:
                await asyncio.sleep(3)

        final_response = {
            'type': 'complete',
            'playlist_id': playlist_id,
            'total_videos': total,
            'videos': [v.model_dump() for v in video_infos],
            'message': f"Processed {processed_count} new videos out of {total} total"
        }
        yield f"data: {json.dumps(final_response)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/playlist", response_model=ProcessPlaylistResponse)
async def process_playlist_endpoint(request: ProcessPlaylistRequest):
    playlist_id = extract_playlist_id(request.playlist_url)
    if not playlist_id:
        raise HTTPException(status_code=400, detail="Invalid playlist URL")

    try:
        videos = get_playlist_videos(request.playlist_url)
    except PlaylistError as e:
        raise HTTPException(status_code=400, detail=str(e))

    video_infos = []
    processed_count = 0
    total = len(videos)

    for idx, video in enumerate(videos):
        vid = video['video_id']

        existing = await Video.find_by_id(vid)
        if existing:
            status = "already_loaded"
        else:
            try:
                transcript, language = process_video(vid)
                engine = RAGEngine()
                engine.load_or_ingest_transcript(transcript, vid)
                engine_store[vid] = engine
                chunks = len(transcript) // 500 + 1

                db_video = await Video.create(vid, language, chunks)
                await Video.insert(db_video)
                status = "processed"
                processed_count += 1
            except Exception as e:
                status = f"error: {str(e)[:50]}"

        video_infos.append(PlaylistVideoInfo(
            video_id=vid,
            title=video['title'],
            duration=video.get('duration', 0),
            url=video['url'],
            status=status,
            progress=f"{idx + 1}/{total}"
        ))

    return ProcessPlaylistResponse(
        playlist_id=playlist_id,
        total_videos=total,
        videos=video_infos,
        message=f"Processed {processed_count} new videos out of {total} total"
    )


# --- Chat & Session Routes ---

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    video_id = extract_video_id(request.video_id)

    existing_video = await Video.find_by_id(video_id)
    if not existing_video:
        raise HTTPException(status_code=404, detail="Video not found. Please process the video first.")

    engine = get_engine(video_id)

    session_id = request.session_id
    if session_id:
        chat_session = await ChatSession.find_by_id(session_id)
        if not chat_session or chat_session["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        title = request.question[:30] + "..." if len(request.question) > 30 else request.question
        new_session = await ChatSession.create(current_user["id"], video_id, title)
        session_id = await ChatSession.insert(new_session)

    history_msgs = await ChatMessage.find_by_session(session_id)
    chat_history = []
    for msg in history_msgs:
        if msg["role"] == "user":
            chat_history.append(HumanMessage(content=msg["content"]))
        else:
            chat_history.append(AIMessage(content=msg["content"]))

    user_msg = await ChatMessage.create(session_id, "user", request.question)
    await ChatMessage.insert(user_msg)

    async def generate():
        full_answer = ""
        try:
            async for chunk in engine.aanswer_stream(request.question, chat_history):
                if chunk.startswith("Error:"):
                    yield chunk
                    full_answer = chunk
                    break
                full_answer += chunk
                yield chunk
        except Exception as e:
            error_msg = f"\n\nError: {str(e)}"
            yield error_msg
            full_answer = error_msg
        finally:
            try:
                if full_answer and not full_answer.startswith("\n\nError:"):
                    ai_msg = await ChatMessage.create(session_id, "assistant", full_answer)
                    await ChatMessage.insert(ai_msg)
            except Exception as ex:
                print(f"Failed to save message: {ex}")

    return StreamingResponse(generate(), media_type="text/plain", headers={"X-Session-ID": session_id})


@router.get("/sessions", response_model=List[SessionInfo])
async def get_user_sessions(current_user: dict = Depends(get_current_user)):
    sessions = await ChatSession.find_by_user(current_user["id"])
    result = []
    for s in sessions:
        messages = await ChatMessage.find_by_session(s["id"])
        result.append(SessionInfo(
            id=s["id"],
            video_id=s["video_id"],
            title=s["title"],
            created_at=s["created_at"].isoformat(),
            message_count=len(messages)
        ))
    return result


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, current_user: dict = Depends(get_current_user)):
    session = await ChatSession.find_by_id(session_id)
    if not session or session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = await ChatMessage.find_by_session(session_id)
    return [{"role": m["role"], "content": m["content"]} for m in messages]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", videos_loaded=0)


@router.delete("/videos/{video_id}")
async def delete_video(video_id: str):
    video = await Video.find_by_id(video_id)
    if video:
        from src.database import get_db
        db = get_db()
        await db.videos.delete_one({"id": video_id})
        if video_id in engine_store:
            del engine_store[video_id]
        return {"message": f"Video {video_id} deleted"}
    raise HTTPException(status_code=404, detail="Video not found")