"""RAG Engine for YouTube Chatbot using Pinecone + sentence-transformers."""
from __future__ import annotations

import asyncio
import os
from typing import Optional, AsyncGenerator, List, Any

from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from .config import RAGConfig, LLMConfig, StorageConfig
from .tracing import traceable, trace_embedder


_shared_embedding_model = None


def get_embedding_model():
    global _shared_embedding_model
    if _shared_embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _shared_embedding_model = trace_embedder(SentenceTransformer("all-MiniLM-L6-v2"))
    return _shared_embedding_model


class RAGEngine:
    """RAG engine using Pinecone + sentence-transformers."""

    def __init__(self) -> None:
        self._llm = None
        self._embedding_model = None
        self._retriever = None
        self._chain = None
        self._qa_chain = None
        self._history_aware_retriever = None
        self._splitter = None
        self._video_id: Optional[str] = None
        self._index = None
        self._extra_context: str = ""

    def set_extra_context(self, text: str) -> None:
        self._extra_context = text

    @property
    def splitter(self):
        if self._splitter is None:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            self._splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100,
            )
        return self._splitter

    @property
    def embedding_model(self):
        return get_embedding_model()

    @property
    def llm(self):
        if self._llm is None:
            from langchain_openai import ChatOpenAI

            if LLMConfig.LLM_PROVIDER == "nvidia":
                api_key = LLMConfig.NVIDIA_API_KEY or os.environ.get("NVIDIA_API_KEY", "")
                self._llm = ChatOpenAI(
                    base_url=LLMConfig.NVIDIA_BASE_URL,
                    api_key=api_key,
                    model=LLMConfig.NVIDIA_MODEL,
                    temperature=LLMConfig.TEMPERATURE,
                    top_p=LLMConfig.TOP_P,
                    max_tokens=LLMConfig.MAX_TOKENS,
                    streaming=True,
                )
            elif LLMConfig.LLM_PROVIDER == "gemini":
                api_key = LLMConfig.GOOGLE_API_KEY or os.environ.get("GOOGLE_API_KEY", "")
                from langchain_google_genai import ChatGoogleGenerativeAI
                self._llm = ChatGoogleGenerativeAI(
                    google_api_key=api_key,
                    model=LLMConfig.MODEL,
                    temperature=LLMConfig.TEMPERATURE,
                    top_p=LLMConfig.TOP_P,
                    max_output_tokens=LLMConfig.MAX_TOKENS,
                    streaming=True,
                )
            else:
                api_key = LLMConfig.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY", "")
                self._llm = ChatOpenAI(
                    base_url=LLMConfig.OPENROUTER_BASE_URL,
                    api_key=api_key,
                    model=LLMConfig.MODEL,
                    temperature=LLMConfig.TEMPERATURE,
                    top_p=LLMConfig.TOP_P,
                    max_tokens=LLMConfig.MAX_TOKENS,
                    streaming=True,
                )
        return self._llm

    def _get_pinecone_index(self):
        from pinecone import Pinecone, ServerlessSpec
        pc = Pinecone(api_key=StorageConfig.PINECONE_API_KEY)
        index_name = StorageConfig.PINECONE_INDEX_NAME
        
        if not pc.has_index(index_name):
            pc.create_index(
                name=index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        
        return pc.Index(index_name)

    def _namespace_exists(self, namespace: str) -> bool:
        try:
            stats = self._index.describe_index_stats()
            namespaces = stats.get("namespaces", {})
            if namespace in namespaces:
                return namespaces[namespace].get("vector_count", 0) > 0
            return False
        except Exception:
            return False

    @traceable(run_type="chain", name="load_or_ingest_transcript")
    def load_or_ingest_transcript(self, transcript: str, video_id: str, playlist_id: str = None, position: int = None) -> None:
        self._video_id = video_id
        self._index = self._get_pinecone_index()
        
        transcript = transcript[:100000] if transcript else ""
        
        namespace_exists = self._namespace_exists(video_id)
        if namespace_exists and playlist_id:
            self._index.delete(delete_all=True, namespace=video_id)
            namespace_exists = False
            print(f"Re-ingesting {video_id} with playlist metadata")
        elif namespace_exists:
            print(f"Using cached namespace: {video_id}")

        if not namespace_exists:
            print(f"Ingesting transcript: {video_id}")
            
            doc_metadata = {"video_id": video_id}
            if playlist_id:
                doc_metadata["playlist_id"] = playlist_id
                doc_metadata["position"] = position
            
            documents = self.splitter.create_documents(
                texts=[transcript],
                metadatas=[doc_metadata]
            )
            
            texts = [doc.page_content for doc in documents]
            embeddings = self.embedding_model.encode(texts).tolist()
            
            vectors = []
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                metadata = {
                    "text": text,
                    "video_id": video_id
                }
                if playlist_id:
                    metadata["playlist_id"] = playlist_id
                    metadata["position"] = position
                vectors.append({
                    "id": f"{video_id}_{i}",
                    "values": embedding,
                    "metadata": metadata
                })
            
            for i in range(0, len(vectors), 50):
                batch = vectors[i:i+50]
                self._index.upsert(
                    vectors=batch,
                    namespace=video_id
                )
            
            print(f"Indexed {len(vectors)} chunks")

        self._retriever = PineconeRetriever(
            index=self._index,
            embedding_model=self.embedding_model,
            video_id=video_id,
            top_k=RAGConfig.TOP_K_RESULTS
        )
        self._build_chain()

    @traceable(run_type="chain", name="_build_chain")
    def _build_chain(self) -> None:
        if self._retriever is None:
            raise RuntimeError("Retriever not initialized")

        from langchain.chains import (
            create_history_aware_retriever,
            create_retrieval_chain,
        )
        from langchain.chains.combine_documents import (
            create_stuff_documents_chain,
        )
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        contextualize_q_system_prompt = (
            "Given a chat history and the latest user question, "
            "reformulate the question into a standalone question."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        
        history_aware_retriever = create_history_aware_retriever(
            self.llm, self._retriever, contextualize_q_prompt
        )
        self._history_aware_retriever = history_aware_retriever

        # Escape braces inside the playlist context to avoid LangChain prompt template syntax errors
        extra = self._extra_context.replace("{", "{{").replace("}", "}}")
        qa_system_prompt = (
            "You are an expert teacher explaining concepts from a YouTube video.\n\n"
            "### Teaching Style:\n"
            "1. Use the Video Context below as your primary source — explain concepts the way the speaker does.\n"
            "2. Match the speaker's tone: if they use analogies, keep using those analogies. If they build up step by step, do the same.\n"
            "3. Start with the big picture intuition, then zoom into details — just like a good teacher would.\n"
            "4. Use plain, simple language. Pretend you're explaining to someone who has never heard of the topic.\n"
            "5. Cite timestamps [MM:SS] from the video context when referencing specific parts.\n"
            "6. If the user's question connects to ideas from other videos in the playlist (see Playlist Context below), "
            "briefly reference those connections to create a flowing narrative across lessons.\n"
            "7. If the answer isn't fully covered by the transcripts, supplement with your own knowledge — "
            "but keep the explanation in the same intuitive style.\n"
            f"{extra}"
            "\n\n### Video Context (from transcript):\n{context}"
        )
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])

        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        self._qa_chain = question_answer_chain
        
        self._chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    def rebuild_chain(self) -> None:
        self._chain = None
        self._qa_chain = None
        self._history_aware_retriever = None
        if self._retriever is not None:
            self._build_chain()
        return self._chain is not None

    def answer(self, question: str, chat_history: list = None) -> str:
        if self._chain is None:
            raise RuntimeError("RAG engine not initialized")
        if chat_history is None:
            chat_history = []
        result = self._chain.invoke({"input": question, "chat_history": chat_history})
        return result["answer"]

    @traceable(run_type="chain", name="aanswer_stream")
    async def aanswer_stream(self, question: str, chat_history: list = None) -> AsyncGenerator[str, None]:
        if self._qa_chain is None or self._retriever is None:
            raise RuntimeError("RAG engine not initialized")
        if chat_history is None:
            chat_history = []

        # Trim chat history to last 6 messages (3 turns) to reduce token count
        chat_history = chat_history[-6:]

        try:
            # Build an enriched retrieval query by appending recent user messages
            # This handles follow-ups like "explain that more" without an LLM call
            from langchain_core.messages import HumanMessage as HMsg
            recent_user_msgs = [
                m.content for m in chat_history[-4:]
                if isinstance(m, HMsg)
            ][-2:]  # Last 2 user messages
            enriched_query = " ".join(recent_user_msgs + [question])

            # Retrieve directly — no LLM reformulation needed
            docs = await self._retriever.ainvoke(enriched_query)

            # Stream the answer (the QA chain still has full chat_history for conversational context)
            async for chunk in self._qa_chain.astream({
                "input": question,
                "chat_history": chat_history,
                "context": docs
            }):
                if isinstance(chunk, str):
                    yield chunk
                elif hasattr(chunk, "content"):
                    yield str(chunk.content)
                elif isinstance(chunk, dict) and "answer" in chunk:
                    yield chunk["answer"]
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"Error: {str(e)}"

    @property
    def is_ready(self) -> bool:
        return self._chain is not None


class PineconeRetriever(BaseRetriever):
    index: object = Field(default=None)
    video_id: str = Field(default="")
    top_k: int = Field(default=5)
    _embedding_model = None

    @property
    def embedding_model(self):
        return get_embedding_model()

    def _get_relevant_documents(self, query: str) -> list:
        from langchain_core.documents import Document
        query_embedding = self.embedding_model.encode(query).tolist()
        
        results = self.index.query(
            vector=query_embedding,
            top_k=self.top_k,
            include_metadata=True,
            namespace=self.video_id
        )
        
        docs = []
        for match in results.matches:
            text = match.metadata.get("text", "") if match.metadata else ""
            docs.append(Document(page_content=text, metadata={"text": text}))
        return docs

    async def _aget_relevant_documents(self, query: str) -> list:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_relevant_documents, query)
