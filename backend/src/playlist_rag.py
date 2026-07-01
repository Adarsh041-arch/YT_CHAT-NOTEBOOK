"""Playlist-level RAG: load, relate, and query across playlist videos."""
from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncGenerator

from .config import RAGConfig
from .tracing import traceable, trace_embedder
from .video_processor import (
    get_transcript_with_timestamps,
    format_transcript,
    get_playlist_videos,
    extract_playlist_id,
    VideoProcessingError,
    PlaylistError,
)


class PlaylistRAG:
    """Orchestrates playlist-level transcript ingestion and querying."""

    FAILURE_CACHE_TTL: int = 3600

    def __init__(self) -> None:
        self._failure_cache: dict[str, float] = {}
        self._relation_cache: dict[str, dict[str, list[str]]] = {}
        self._index = None
        self._embedding_model = None
        self._llm = None

    @property
    def _pinecone_index(self):
        if self._index is None:
            from pinecone import Pinecone
            from .config import StorageConfig
            pc = Pinecone(api_key=StorageConfig.PINECONE_API_KEY)
            self._index = pc.Index(StorageConfig.PINECONE_INDEX_NAME)
        return self._index

    @property
    def _embedder(self):
        from .rag_engine import get_embedding_model
        return get_embedding_model()

    @property
    def _llm_instance(self):
        if self._llm is None:
            from langchain_openai import ChatOpenAI
            from .config import LLMConfig
            import os
            if LLMConfig.LLM_PROVIDER == "nvidia":
                self._llm = ChatOpenAI(
                    base_url=LLMConfig.NVIDIA_BASE_URL,
                    api_key=LLMConfig.NVIDIA_API_KEY or os.environ.get("NVIDIA_API_KEY", ""),
                    model=LLMConfig.NVIDIA_MODEL,
                    temperature=LLMConfig.TEMPERATURE,
                    top_p=LLMConfig.TOP_P,
                    max_tokens=LLMConfig.MAX_TOKENS,
                    streaming=True,
                )
            elif LLMConfig.LLM_PROVIDER == "gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI
                self._llm = ChatGoogleGenerativeAI(
                    google_api_key=LLMConfig.GOOGLE_API_KEY or os.environ.get("GOOGLE_API_KEY", ""),
                    model=LLMConfig.MODEL,
                    temperature=LLMConfig.TEMPERATURE,
                    top_p=LLMConfig.TOP_P,
                    max_output_tokens=LLMConfig.MAX_TOKENS,
                    streaming=True,
                )
            else:
                self._llm = ChatOpenAI(
                    base_url=LLMConfig.OPENROUTER_BASE_URL,
                    api_key=LLMConfig.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY", ""),
                    model=LLMConfig.MODEL,
                    temperature=LLMConfig.TEMPERATURE,
                    top_p=LLMConfig.TOP_P,
                    max_tokens=LLMConfig.MAX_TOKENS,
                    streaming=True,
                )
        return self._llm

    # ── Load playlist ─────────────────────────────────────────────

    @traceable(run_type="chain", name="load_playlist")
    async def load_playlist(self, playlist_url: str) -> dict:
        playlist_id = extract_playlist_id(playlist_url)
        if not playlist_id:
            raise PlaylistError("Could not extract playlist ID from URL")

        videos = get_playlist_videos(playlist_url)
        if not videos:
            raise PlaylistError("No videos found in playlist")

        total = len(videos)
        sem = asyncio.Semaphore(1)
        results: list[dict | None] = [None] * total

        async def _process(idx: int, video: dict) -> dict:
            async with sem:
                vid = video["video_id"]
                last_fail = self._failure_cache.get(vid)
                if last_fail and (time.time() - last_fail) < self.FAILURE_CACHE_TTL:
                    return {"video_id": vid, "title": video.get("title", ""), "position": idx, "status": "skipped", "error": "cached failure"}

                from .database import PlaylistVideo
                existing = await PlaylistVideo.find_by_playlist_video(playlist_id, vid)
                if existing:
                    return {"video_id": vid, "title": video.get("title", ""), "position": idx, "status": "already_loaded", "summary": existing.get("summary", "")}

                try:
                    items, lang = await get_transcript_with_timestamps(vid)
                    transcript = format_transcript(items)
                    summary = transcript[:500]

                    from .rag_engine import RAGEngine
                    engine = RAGEngine()
                    engine.load_or_ingest_transcript(transcript, vid, playlist_id=playlist_id, position=idx)

                    await PlaylistVideo.create(
                        playlist_id=playlist_id, video_id=vid,
                        title=video.get("title", ""), position=idx,
                        summary=summary, language=lang,
                    )

                    return {"video_id": vid, "title": video.get("title", ""), "position": idx, "status": "processed", "summary": summary}

                except VideoProcessingError as e:
                    self._failure_cache[vid] = time.time()
                    return {"video_id": vid, "title": video.get("title", ""), "position": idx, "status": "failed", "error": str(e)}

        tasks = [_process(i, v) for i, v in enumerate(videos)]
        task_results = await asyncio.gather(*tasks)

        succeeded = [r for r in task_results if r and r["status"] in ("processed", "already_loaded")]
        graph = self._build_relation_graph(succeeded) if succeeded else {}

        from .database import PlaylistResult
        await PlaylistResult.upsert(playlist_id, graph, videos=videos)

        failed = [r for r in task_results if r and r["status"] in ("failed", "skipped")]

        return {
            "playlist_id": playlist_id,
            "total": total,
            "succeeded": [r["video_id"] for r in succeeded],
            "failed": [{"video_id": r["video_id"], "error": r.get("error", "")} for r in failed],
            "videos": task_results,
            "relation_graph": graph,
        }

    # ── Relation graph ────────────────────────────────────────────

    @traceable(run_type="chain", name="_build_relation_graph")
    def _build_relation_graph(self, videos: list[dict]) -> dict[str, list[str]]:
        from sklearn.metrics.pairwise import cosine_similarity
        summaries = [v["summary"] for v in videos]
        video_ids = [v["video_id"] for v in videos]
        if len(videos) == 1:
            return {video_ids[0]: []}
        embeddings = self._embedder.encode(summaries)
        sim_matrix = cosine_similarity(embeddings)
        graph: dict[str, list[str]] = {}
        for i, vid in enumerate(video_ids):
            scores = [(j, sim_matrix[i][j]) for j in range(len(video_ids)) if j != i]
            scores.sort(key=lambda x: -x[1])
            graph[vid] = [video_ids[j] for j, _ in scores[:3]]
        return graph

    # ── Query ─────────────────────────────────────────────────────

    @traceable(run_type="chain", name="answer_question")
    async def answer_question(
        self, playlist_id: str, question: str, chat_history: list | None = None,
    ) -> AsyncGenerator[str, None]:
        if chat_history is None:
            chat_history = []
        if self._detect_relation_question(question):
            async for chunk in self._answer_with_relation(playlist_id, question, chat_history):
                yield chunk
        else:
            async for chunk in self._answer_standard(playlist_id, question, chat_history):
                yield chunk

    def _detect_relation_question(self, question: str) -> bool:
        keywords = [
            "relate", "compare", "similar", "difference", "connection",
            "how does", "how do", "versus", "vs", "contrast",
            "relation between", "tie together", "linked", "different",
            "compare and contrast",
        ]
        q = question.lower()
        return any(kw in q for kw in keywords)

    @traceable(run_type="chain", name="_answer_standard")
    async def _answer_standard(self, playlist_id: str, question: str, chat_history: list) -> AsyncGenerator[str, None]:
        from langchain_core.documents import Document
        from langchain_core.messages import HumanMessage, AIMessage
        from langchain_core.prompts import ChatPromptTemplate

        query_emb = self._embedder.encode(question).tolist()
        results = self._pinecone_index.query(
            vector=query_emb, top_k=RAGConfig.TOP_K_RESULTS * 3,
            include_metadata=True, filter={"playlist_id": {"$eq": playlist_id}},
        )

        docs = []
        for match in results.matches:
            text = match.metadata.get("text", "")
            vid = match.metadata.get("video_id", "")
            pos = match.metadata.get("position", 0)
            if text:
                docs.append(Document(page_content=text, metadata={"video_id": vid, "position": pos}))

        if not docs:
            yield "No relevant content found in this playlist's transcripts."
            return

        context = "\n\n".join(
            f"[Video position {d.metadata.get('position', '?')}] {d.page_content}" for d in docs
        )

        messages = [
            ("system", (
                "You are an expert assistant answering questions about a YouTube playlist.\n\n"
                "The playlist consists of multiple videos. Each chunk is labeled with its video position.\n"
                "Based on the provided transcripts, answer the user's question.\n"
                "When citing information, mention which video position(s) you are referring to.\n"
                "If the answer is not fully covered by the transcripts, supplement with your own knowledge.\n\n"
                "Context:\n{context}"
            )),
        ]
        for msg in chat_history:
            if isinstance(msg, HumanMessage):
                messages.append(("human", msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(("ai", msg.content))
        messages.append(("human", "{input}"))

        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | self._llm_instance

        try:
            async for chunk in chain.astream({"input": question, "context": context}):
                if hasattr(chunk, "content"):
                    yield chunk.content
                elif isinstance(chunk, str):
                    yield chunk
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"\n\nError: {str(e)}"

    @traceable(run_type="chain", name="_answer_with_relation")
    async def _answer_with_relation(self, playlist_id: str, question: str, chat_history: list) -> AsyncGenerator[str, None]:
        from langchain_core.documents import Document
        from langchain_core.messages import HumanMessage, AIMessage
        from langchain_core.prompts import ChatPromptTemplate

        from .database import PlaylistResult, PlaylistVideo

        playlist_data = await PlaylistResult.find_by_id(playlist_id)
        graph = playlist_data.get("relation_graph", {}) if playlist_data else {}
        all_videos = await PlaylistVideo.find_by_playlist(playlist_id)
        id_to_title = {v["video_id"]: v["title"] for v in all_videos}

        q_lower = question.lower()
        mentioned_ids = []
        for v in all_videos:
            title_lower = v["title"].lower()
            title_words = [w for w in title_lower.split() if len(w) > 3]
            if any(w in q_lower for w in title_words) or title_lower in q_lower:
                mentioned_ids.append(v["video_id"])

        neighbor_ids = set()
        for vid in mentioned_ids:
            neighbor_ids.update(graph.get(vid, []))
        neighbor_ids.difference_update(mentioned_ids)

        query_emb = self._embedder.encode(question).tolist()
        results = self._pinecone_index.query(
            vector=query_emb, top_k=RAGConfig.TOP_K_RESULTS * 3,
            include_metadata=True, filter={"playlist_id": {"$eq": playlist_id}},
        )

        context_parts = []
        seen_vids = set()
        for match in results.matches:
            vid = match.metadata.get("video_id", "")
            if vid in seen_vids:
                continue
            seen_vids.add(vid)
            text = match.metadata.get("text", "")
            pos = match.metadata.get("position", 0)
            title = id_to_title.get(vid, "Unknown")
            neighbors = graph.get(vid, [])
            neighbor_titles = [id_to_title.get(n, n) for n in neighbors[:2]]
            relation_info = ""
            if neighbor_titles:
                relation_info = f" (related to: {', '.join(neighbor_titles)})"
            context_parts.append(f"[Video: {title}{relation_info}]\n{text}")

        context = "\n\n".join(context_parts)

        messages = [
            ("system", (
                "You are an expert assistant analyzing relationships between videos in a YouTube playlist.\n\n"
                "The playlist contains multiple videos. Below are transcript excerpts along with which videos "
                "they come from and which other videos they are related to.\n\n"
                "Answer the user's question, explaining how the videos connect to each other. "
                "Use the transcript context to support your explanation. "
                "Mention specific video titles when referring to connections.\n\n"
                "Context:\n{context}"
            )),
        ]
        for msg in chat_history:
            if isinstance(msg, HumanMessage):
                messages.append(("human", msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(("ai", msg.content))
        messages.append(("human", "{input}"))

        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | self._llm_instance

        try:
            async for chunk in chain.astream({"input": question, "context": context}):
                if hasattr(chunk, "content"):
                    yield chunk.content
                elif isinstance(chunk, str):
                    yield chunk
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"\n\nError: {str(e)}"
