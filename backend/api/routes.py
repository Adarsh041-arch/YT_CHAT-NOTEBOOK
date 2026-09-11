"""FastAPI routes for YTChatBot API."""

import os
import uuid
import re
import json
import asyncio
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm

from src.tracing import traceable

from src.rag_engine import RAGEngine, PineconeRetriever
from src.video_processor import process_video, VideoProcessingError, get_playlist_videos, extract_playlist_id, PlaylistError, get_transcript_with_timestamps, format_transcript
from src.playlist_rag import PlaylistRAG
from src.database import Video, ChatSession, ChatMessage, User, PlaylistResult, PlaylistVideo, VisualizationCache, VisualizationLog
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
    PlaylistVideoInfo,
    PlaylistLoadResponse,
    PlaylistQueryRequest,
    PlaylistInfo,
    VisualizationRequest,
    LogValidationRequest,
    RegenerateVisualizationRequest,
)
from .viz_utils import classify_visualization, generate_viz_spec, regenerate_viz_spec

router = APIRouter()

engine_store: dict[str, RAGEngine] = {}
_playlist_rag: PlaylistRAG | None = None
_video_playlist_cache: dict[str, str | None] = {}


def _get_playlist_rag() -> PlaylistRAG:
    global _playlist_rag
    if _playlist_rag is None:
        _playlist_rag = PlaylistRAG()
    return _playlist_rag


async def _run_blocking(callable, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: callable(*args, **kwargs))


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
@traceable(run_type="chain", name="process_video_endpoint")
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
        transcript, language = await process_video(video_id)
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
@traceable(run_type="chain", name="process_playlist_stream")
async def process_playlist_stream(request: ProcessPlaylistRequest):
    import asyncio
    import json
    import time
    import traceback
    import sys

    playlist_id = extract_playlist_id(request.playlist_url)
    if not playlist_id:
        raise HTTPException(status_code=400, detail="Invalid playlist URL")

    try:
        videos = get_playlist_videos(request.playlist_url)
    except PlaylistError as e:
        raise HTTPException(status_code=400, detail=str(e))

    total = len(videos)
    all_video_status = {}
    rag = PlaylistRAG()

    async def generate():
        yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"
        succeeded_list = []

        for idx, video in enumerate(videos):
            vid = video["video_id"]
            yield f"data: {json.dumps({'type': 'progress', 'current': idx + 1, 'total': total, 'video_id': vid, 'title': video['title']})}\n\n"

            try:
                items, lang = await get_transcript_with_timestamps(vid)
                transcript = format_transcript(items)

                loop = asyncio.get_event_loop()
                engine = RAGEngine()
                await loop.run_in_executor(None, engine.load_or_ingest_transcript, transcript, vid, playlist_id, idx)
                engine_store[vid] = engine

                summary = transcript[:500]
                await PlaylistVideo.create(
                    playlist_id=playlist_id, video_id=vid,
                    title=video.get("title", ""), position=idx,
                    summary=summary, language=lang,
                )

                all_video_status[vid] = {"video_id": vid, "title": video["title"], "status": "processed"}
                yield f"data: {json.dumps({'type': 'video_done', 'video': all_video_status[vid]})}\n\n"
                succeeded_list.append({"video_id": vid, "summary": summary})

            except Exception as e:
                traceback.print_exc()
                all_video_status[vid] = {"video_id": vid, "title": video["title"], "status": f"error: {str(e)[:80]}"}
                yield f"data: {json.dumps({'type': 'video_done', 'video': all_video_status[vid]})}\n\n"

            await asyncio.sleep(3)

        all_playlist_videos = await PlaylistVideo.find_by_playlist(playlist_id)
        all_succeeded = [{"video_id": v["video_id"], "summary": v.get("summary", "")} for v in all_playlist_videos]
        graph = rag._build_relation_graph(all_succeeded) if all_succeeded else {}
        await PlaylistResult.upsert(playlist_id, graph, videos=videos)

        yield f"data: {json.dumps({'type': 'complete', 'playlist_id': playlist_id, 'total_videos': total, 'videos': list(all_video_status.values()), 'relation_graph': graph})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/playlist", response_model=PlaylistLoadResponse)
@traceable(run_type="chain", name="process_playlist_endpoint")
async def process_playlist_endpoint(request: ProcessPlaylistRequest):
    try:
        rag = PlaylistRAG()
        result = await rag.load_playlist(request.playlist_url)
        return PlaylistLoadResponse(**result)
    except PlaylistError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post("/playlist/query")
@traceable(run_type="chain", name="playlist_query_endpoint")
async def playlist_query_endpoint(request: PlaylistQueryRequest, current_user: dict = Depends(get_current_user)):
    id_to_title = {}
    all_videos = await PlaylistVideo.find_by_playlist(request.playlist_id)
    if not all_videos:
        raise HTTPException(status_code=404, detail="Playlist not found. Process it first.")
    for v in all_videos:
        id_to_title[v["video_id"]] = v["title"]

    chat_history = []
    if request.session_id:
        session = await ChatSession.find_by_id(request.session_id)
        if session and session["user_id"] == current_user["id"]:
            history_msgs = await ChatMessage.find_by_session(request.session_id)
            for msg in history_msgs:
                if msg["role"] == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                else:
                    chat_history.append(AIMessage(content=msg["content"]))

    if not request.session_id:
        title = request.question[:30] + "..." if len(request.question) > 30 else request.question
        new_session = await ChatSession.create(current_user["id"], request.playlist_id, title)
        request.session_id = await ChatSession.insert(new_session)

    user_msg = await ChatMessage.create(request.session_id, "user", request.question)
    await ChatMessage.insert(user_msg)

    rag = PlaylistRAG()

    async def generate():
        full_answer = ""
        try:
            async for chunk in rag.answer_question(request.playlist_id, request.question, chat_history):
                full_answer += chunk
                yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"\n\nError: {str(e)}"
            yield f"event: token\ndata: {json.dumps({'text': error_msg})}\n\n"
            full_answer = error_msg
        finally:
            yield "event: done\ndata: {}\n\n"
            if full_answer and not full_answer.startswith("\n\nError:"):
                ai_msg = await ChatMessage.create(request.session_id, "assistant", full_answer)
                await ChatMessage.insert(ai_msg)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"X-Session-ID": request.session_id})


@router.get("/playlists", response_model=list[PlaylistInfo])
async def list_playlists(current_user: dict = Depends(get_current_user)):
    from src.database import get_db
    db = get_db()
    cursor = db.playlist_results.find().sort("created_at", -1)
    results = []
    async for doc in cursor:
        videos_cursor = db.playlist_videos.find({"playlist_id": doc["playlist_id"]})
        video_count = await videos_cursor.to_list(length=None)
        results.append(PlaylistInfo(
            playlist_id=doc["playlist_id"],
            total_videos=len(video_count),
            created_at=doc.get("created_at", datetime(2020, 1, 1)).isoformat(),
        ))
    return results


@router.post("/playlist/retry/stream")
@traceable(run_type="chain", name="retry_playlist_stream")
async def retry_playlist_stream(request: ProcessPlaylistRequest):
    import asyncio
    import json
    import traceback

    playlist_id = extract_playlist_id(request.playlist_url)
    if not playlist_id:
        raise HTTPException(status_code=400, detail="Invalid playlist URL")

    try:
        all_videos = get_playlist_videos(request.playlist_url)
    except PlaylistError as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing = await PlaylistVideo.find_by_playlist(playlist_id)
    existing_ids = {v["video_id"] for v in existing}
    videos_to_retry = [v for v in all_videos if v["video_id"] not in existing_ids]

    if not videos_to_retry:
        async def noop():
            yield f"data: {json.dumps({'type': 'complete', 'playlist_id': playlist_id, 'total_videos': 0, 'videos': [], 'message': 'All videos already processed'})}\n\n"
        return StreamingResponse(noop(), media_type="text/event-stream")

    total = len(videos_to_retry)
    rag = PlaylistRAG()
    succeeded_list = []

    async def generate():
        yield f"data: {json.dumps({'type': 'start', 'total': total, 'retry': True})}\n\n"

        for idx, video in enumerate(videos_to_retry):
            vid = video["video_id"]
            yield f"data: {json.dumps({'type': 'progress', 'current': idx + 1, 'total': total, 'video_id': vid, 'title': video['title']})}\n\n"

            try:
                loop = asyncio.get_event_loop()
                items, lang = await get_transcript_with_timestamps(vid)
                transcript = format_transcript(items)

                engine = RAGEngine()
                await loop.run_in_executor(None, engine.load_or_ingest_transcript, transcript, vid, playlist_id, idx)
                engine_store[vid] = engine

                summary = transcript[:500]
                await PlaylistVideo.create(
                    playlist_id=playlist_id, video_id=vid,
                    title=video.get("title", ""), position=idx,
                    summary=summary, language=lang,
                )

                yield f"data: {json.dumps({'type': 'video_done', 'video': {'video_id': vid, 'title': video['title'], 'status': 'processed'}})}\n\n"
                succeeded_list.append({"video_id": vid, "summary": summary})

            except Exception as e:
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'video_done', 'video': {'video_id': vid, 'title': video['title'], 'status': f'error: {str(e)[:80]}'}})}\n\n"

            await asyncio.sleep(3)

        all_playlist_videos = await PlaylistVideo.find_by_playlist(playlist_id)
        all_succeeded = [{"video_id": v["video_id"], "summary": v.get("summary", "")} for v in all_playlist_videos]
        graph = rag._build_relation_graph(all_succeeded) if all_succeeded else {}
        await PlaylistResult.upsert(playlist_id, graph, videos=all_videos)

        yield f"data: {json.dumps({'type': 'complete', 'playlist_id': playlist_id, 'total_videos': total, 'videos': succeeded_list, 'relation_graph': graph})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/playlist/retry")
@traceable(run_type="chain", name="retry_playlist_endpoint")
async def retry_playlist_endpoint(request: ProcessPlaylistRequest):
    import asyncio
    playlist_id = extract_playlist_id(request.playlist_url)
    if not playlist_id:
        raise HTTPException(status_code=400, detail="Invalid playlist URL")
    try:
        all_videos = get_playlist_videos(request.playlist_url)
    except PlaylistError as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing = await PlaylistVideo.find_by_playlist(playlist_id)
    existing_ids = {v["video_id"] for v in existing}
    videos_to_retry = [v for v in all_videos if v["video_id"] not in existing_ids]

    if not videos_to_retry:
        return {"playlist_id": playlist_id, "total": 0, "message": "All videos already processed"}

    rag = PlaylistRAG()
    sem = asyncio.Semaphore(1)

    async def process_one(video):
        async with sem:
            vid = video["video_id"]
            try:
                items, lang = await get_transcript_with_timestamps(vid)
                transcript = format_transcript(items)
                summary = transcript[:500]
                engine = RAGEngine()
                engine.load_or_ingest_transcript(transcript, vid, playlist_id=playlist_id, position=0)
                engine_store[vid] = engine
                await PlaylistVideo.create(playlist_id=playlist_id, video_id=vid, title=video.get("title", ""), position=0, summary=summary, language=lang)
                return {"video_id": vid, "title": video["title"], "status": "processed"}
            except Exception as e:
                return {"video_id": vid, "title": video["title"], "status": f"error: {str(e)[:80]}"}

    results = await asyncio.gather(*[process_one(v) for v in videos_to_retry])

    all_playlist_videos = await PlaylistVideo.find_by_playlist(playlist_id)
    all_succeeded = [{"video_id": v["video_id"], "summary": v.get("summary", "")} for v in all_playlist_videos]
    graph = rag._build_relation_graph(all_succeeded) if all_succeeded else {}
    await PlaylistResult.upsert(playlist_id, graph, videos=all_videos)

    return {"playlist_id": playlist_id, "total": len(videos_to_retry), "results": results, "relation_graph": graph}


@router.get("/playlist/for-video/{video_id}")
async def get_playlist_for_video(video_id: str):
    """If video belongs to a processed playlist, return playlist info + all videos with status."""
    from src.database import get_db
    db = get_db()
    vid_playlists = await PlaylistVideo.find_playlists_for_video(video_id)
    if not vid_playlists:
        return {"playlist_id": None, "videos": []}
    pl_id = vid_playlists[0]["playlist_id"]
    pl_data = await PlaylistResult.find_by_id(pl_id)
    if not pl_data:
        return {"playlist_id": pl_id, "videos": []}
    raw_videos = pl_data.get("videos", [])
    processed = await PlaylistVideo.find_by_playlist(pl_id)
    processed_ids = {v["video_id"] for v in processed}
    videos_out = []
    for v in raw_videos:
        status = "processed" if v["video_id"] in processed_ids else "pending"
        videos_out.append({
            "video_id": v["video_id"],
            "title": v.get("title", ""),
            "status": status,
            "position": next((p.get("position", 0) for p in processed if p["video_id"] == v["video_id"]), 0),
        })
    return {"playlist_id": pl_id, "videos": videos_out}


# --- Chat & Session Routes ---

@router.post("/chat")
@traceable(run_type="chain", name="chat_endpoint")
async def chat_endpoint(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    video_id = extract_video_id(request.video_id)

    # Parallelize video lookups
    video_result, playlist_video_result = await asyncio.gather(
        Video.find_by_id(video_id),
        PlaylistVideo.find_by_video_id(video_id),
    )
    existing_video = video_result or playlist_video_result
    if not existing_video:
        raise HTTPException(status_code=404, detail="Video not found. Please process the video first.")

    engine = get_engine(video_id)

    # Check if video belongs to a processed playlist — inject neighbor context
    try:
        vid = video_id
        if vid in _video_playlist_cache:
            pl_id = _video_playlist_cache[vid]
        else:
            vid_playlists = await PlaylistVideo.find_playlists_for_video(vid)
            pl_id = vid_playlists[0]["playlist_id"] if vid_playlists else None
            _video_playlist_cache[vid] = pl_id

        if pl_id:
            print(f"[playlist-chat] Video {vid} in playlist {pl_id}")
            pl_data = await PlaylistResult.find_by_id(pl_id)
            graph = pl_data.get("relation_graph", {}) if pl_data else {}
            all_pv = await PlaylistVideo.find_by_playlist(pl_id)
            id_to_title = {v["video_id"]: v["title"] for v in all_pv}
            neighbors = graph.get(vid, [])
            print(f"[playlist-chat] Neighbors: {neighbors}")
            if neighbors:
                loop = asyncio.get_event_loop()
                rag = _get_playlist_rag()
                query_emb = (await _run_blocking(rag._embedder.encode, request.question)).tolist()
                neighbor_lines = []
                seen = set()

                # Query each neighbor namespace in parallel (faster than filter + fallback)
                neighbor_queries = []
                for nid in neighbors[:3]:
                    neighbor_queries.append(
                        _run_blocking(
                            rag._pinecone_index.query,
                            vector=query_emb, top_k=1,
                            include_metadata=True,
                            namespace=nid,
                        )
                    )
                nr_results = await asyncio.gather(*neighbor_queries)
                for nr in nr_results:
                    if nr.matches:
                        m = nr.matches[0]
                        nid = m.metadata.get("video_id", "")
                        if nid not in seen:
                            seen.add(nid)
                            title = id_to_title.get(nid, "Unknown")
                            text = m.metadata.get("text", "")[:400]
                            neighbor_lines.append(f"[{title}]: {text}")

                if neighbor_lines:
                    extra = "\n\n### Playlist Context (related videos in the same playlist):\n" + "\n\n".join(neighbor_lines)
                    print(f"[playlist-chat] Injecting context from {len(seen)} neighbor videos: {list(seen)}")
                    if engine._extra_context != extra:
                        engine.set_extra_context(extra)
                        engine.rebuild_chain()
                else:
                    print("[playlist-chat] No neighbor chunks found — skipping")
    except Exception as e:
        print(f"[playlist-chat] Error injecting neighbor context: {e}")
        import traceback
        traceback.print_exc()

    session_id = request.session_id
    if session_id:
        # Fetch session and history in parallel
        chat_session, history_msgs = await asyncio.gather(
            ChatSession.find_by_id(session_id),
            ChatMessage.find_by_session(session_id),
        )
        if not chat_session or chat_session["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        title = request.question[:30] + "..." if len(request.question) > 30 else request.question
        new_session = await ChatSession.create(current_user["id"], video_id, title)
        session_id = await ChatSession.insert(new_session)
        history_msgs = []

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
        print("=== Starting generate() (SSE) ===")
        try:
            async for chunk in engine.aanswer_stream(request.question, chat_history):
                print(f"Chunk: {chunk[:100] if len(chunk) > 100 else chunk}")
                if chunk.startswith("Error:"):
                    yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
                    full_answer = chunk
                    break
                full_answer += chunk
                yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"\n\nError: {str(e)}"
            yield f"event: token\ndata: {json.dumps({'text': error_msg})}\n\n"
            full_answer = error_msg
        finally:
            yield "event: done\ndata: {}\n\n"
            try:
                if full_answer and not full_answer.startswith("\n\nError:"):
                    ai_msg = await ChatMessage.create(session_id, "assistant", full_answer)
                    await ChatMessage.insert(ai_msg)
            except Exception as ex:
                print(f"Failed to save message: {ex}")

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"X-Session-ID": session_id})


@router.post("/visualize")
@traceable(run_type="chain", name="generate_visualization")
async def generate_visualization(request: VisualizationRequest, current_user: dict = Depends(get_current_user)):
    video_id = extract_video_id(request.video_id)

    # Retrieve context chunks from Pinecone / Check cache
    context_chunks = []
    try:
        engine = get_engine(video_id)
        query_emb = engine.embedding_model.encode(request.question).tolist()
        
        # Check cache first
        cached_spec = await VisualizationCache.find_similar(video_id, query_emb)
        if cached_spec:
            return cached_spec

        if engine._index:
            nr = engine._index.query(
                vector=query_emb, top_k=4,
                include_metadata=True,
                namespace=video_id,
            )
            context_chunks = [m.metadata.get("text", "")[:800] for m in nr.matches if m.metadata]
    except Exception as e:
        print(f"[visualize] Context fetch error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve context: {e}")

    # Classify
    category = await classify_visualization(request.question, context_chunks)
    if category == "none":
        return {"type": "none"}

    # Generate high-quality spec
    spec = await generate_viz_spec(category, request.question, context_chunks)
    if not spec:
        raise HTTPException(status_code=500, detail="Failed to generate visualization spec")

    # If it is generated, store in cache
    try:
        await VisualizationCache.insert(video_id, request.question, query_emb, spec)
    except Exception as e:
        print(f"[visualize] Cache write error: {e}")

    # Log the successful generation
    try:
        await VisualizationLog.log(
            video_id=video_id,
            query=request.question,
            category=category,
            spec=spec,
            validation_error=None
        )
    except Exception as e:
        print(f"[visualize] Log write error: {e}")

    return spec


@router.post("/visualize/log-validation")
@traceable(run_type="chain", name="log_visualization_validation")
async def log_visualization_validation(request: LogValidationRequest, current_user: dict = Depends(get_current_user)):
    video_id = extract_video_id(request.video_id) if request.video_id else ""
    try:
        await VisualizationLog.log(
            video_id=video_id,
            query=request.query,
            category=request.category,
            spec=request.spec,
            validation_error=request.validation_error
        )
        return {"status": "logged"}
    except Exception as e:
        print(f"[visualize-log] Logging error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log validation results: {e}")


@router.post("/visualize/regenerate")
@traceable(run_type="chain", name="regenerate_visualization")
async def regenerate_visualization(request: RegenerateVisualizationRequest, current_user: dict = Depends(get_current_user)):
    video_id = extract_video_id(request.video_id) if request.video_id else ""
    
    spec = await regenerate_viz_spec(
        category=request.category,
        query=request.query,
        failed_code=request.failed_code,
        error_message=request.error_message
    )
    if not spec:
        raise HTTPException(status_code=500, detail="Failed to regenerate visualization spec")
        
    try:
        engine = engine_store.get(video_id)
        if not engine:
            engine = RAGEngine()
            engine.init_retriever(video_id)
            engine_store[video_id] = engine
        
        query_emb = engine.embedding_model.encode(request.query).tolist()
        
        from src.database import get_db, VisualizationCache
        db = get_db()
        cursor = db.visualization_cache.find({"video_id": video_id})
        entries = await cursor.to_list(length=100)
        norm1 = sum(a * a for a in query_emb) ** 0.5
        ids_to_delete = []
        for entry in entries:
            cached_emb = entry.get("query_embedding")
            if not cached_emb:
                continue
            dot = sum(a * b for a, b in zip(query_emb, cached_emb))
            norm2 = sum(b * b for b in cached_emb) ** 0.5
            if norm2 > 0:
                sim = dot / (norm1 * norm2)
                if sim >= 0.90:
                    ids_to_delete.append(entry["_id"])
                    
        if ids_to_delete:
            await db.visualization_cache.delete_many({"_id": {"$in": ids_to_delete}})
            
        await VisualizationCache.insert(video_id, request.query, query_emb, spec)
    except Exception as e:
        print(f"[visualize-regenerate] Cache update error: {e}")
        
    return spec


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


@router.patch("/sessions/{session_id}")
async def update_session_title(session_id: str, body: dict, current_user: dict = Depends(get_current_user)):
    session = await ChatSession.find_by_id(session_id)
    if not session or session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    from src.database import get_db
    await get_db().chat_sessions.update_one({"id": session_id}, {"$set": {"title": title}})
    return {"id": session_id, "title": title}


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