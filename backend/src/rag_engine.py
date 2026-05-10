"""RAG Engine for YouTube Chatbot using Pinecone + sentence-transformers."""

import os
from typing import Optional, AsyncGenerator, List

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.retrievers import BaseRetriever
from pydantic import Field
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

from .config import RAGConfig, LLMConfig, StorageConfig


class RAGEngine:
    """RAG engine using Pinecone + sentence-transformers."""

    def __init__(self) -> None:
        self._llm: Optional[ChatOpenAI] = None
        self._embedding_model: Optional[SentenceTransformer] = None
        self._retriever = None
        self._chain: Optional[Runnable] = None
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
        )
        self._video_id: Optional[str] = None
        self._index = None

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedding_model

    @property
    def llm(self) -> ChatOpenAI:
        if self._llm is None:
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

    def load_or_ingest_transcript(self, transcript: str, video_id: str) -> None:
        self._video_id = video_id
        self._index = self._get_pinecone_index()
        
        transcript = transcript[:100000] if transcript else ""
        
        if self._namespace_exists(video_id):
            print(f"Using cached namespace: {video_id}")
        else:
            print(f"Ingesting transcript: {video_id}")
            
            documents = self._splitter.create_documents(
                texts=[transcript],
                metadatas=[{"video_id": video_id}]
            )
            
            texts = [doc.page_content for doc in documents]
            embeddings = self.embedding_model.encode(texts).tolist()
            
            vectors = []
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                vectors.append({
                    "id": f"{video_id}_{i}",
                    "values": embedding,
                    "metadata": {
                        "text": text,
                        "video_id": video_id
                    }
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

    def _build_chain(self) -> None:
        if self._retriever is None:
            raise RuntimeError("Retriever not initialized")

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
        
        qa_system_prompt = (
            "You are an expert, helpful assistant answering questions about a specific YouTube video.\n\n"
            "### Instructions:\n"
            "1. Use the Video Context: Base your answer on the provided video context below.\n"
            "2. Cite timestamps when available.\n"
            "3. Keep answers concise and natural.\n"
            "4. If info is missing, state that additional knowledge is general knowledge.\n\n"
            "Context:\n{context}"
        )
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])

        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        self._chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    def answer(self, question: str, chat_history: list = None) -> str:
        if self._chain is None:
            raise RuntimeError("RAG engine not initialized")
        if chat_history is None:
            chat_history = []
        result = self._chain.invoke({"input": question, "chat_history": chat_history})
        return result["answer"]

    async def aanswer_stream(self, question: str, chat_history: list = None) -> AsyncGenerator[str, None]:
        if self._chain is None:
            raise RuntimeError("RAG engine not initialized")
        if chat_history is None:
            chat_history = []
        try:
            async for chunk in self._chain.astream({"input": question, "chat_history": chat_history}):
                if "answer" in chunk:
                    yield chunk["answer"]
                elif "context" in chunk:
                    pass
                else:
                    for key, value in chunk.items():
                        if key == "answer" or key == "output_text":
                            yield str(value)
        except Exception as e:
            yield f"Error: {str(e)}"

    @property
    def is_ready(self) -> bool:
        return self._chain is not None


class PineconeRetriever(BaseRetriever):
    index: object = Field(default=None)
    video_id: str = Field(default="")
    top_k: int = Field(default=5)
    _embedding_model: Optional[SentenceTransformer] = None

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedding_model

    def _get_relevant_documents(self, query: str) -> List[Document]:
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

    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        return self._get_relevant_documents(query)