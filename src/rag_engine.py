"""RAG (Retrieval-Augmented Generation) engine for Q&A."""

from typing import Optional

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableParallel,
    RunnableLambda,
    RunnablePassthrough,
)
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import RAGConfig, LLMConfig


class RAGEngine:
    """RAG engine for processing transcripts and answering questions."""

    def __init__(self) -> None:
        self._embeddings: Optional[GoogleGenerativeAIEmbeddings] = None
        self._llm: Optional[ChatGoogleGenerativeAI] = None
        self._retriever = None
        self._chain: Optional[Runnable] = None
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=RAGConfig.CHUNK_SIZE,
            chunk_overlap=RAGConfig.CHUNK_OVERLAP,
        )

    @property
    def embeddings(self) -> GoogleGenerativeAIEmbeddings:
        """Lazy initialization of embeddings model."""
        if self._embeddings is None:
            self._embeddings = GoogleGenerativeAIEmbeddings(
                model=LLMConfig.EMBEDDING_MODEL
            )
        return self._embeddings

    @property
    def llm(self) -> ChatGoogleGenerativeAI:
        """Lazy initialization of chat model."""
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=LLMConfig.MODEL,
                temperature=LLMConfig.TEMPERATURE,
            )
        return self._llm

    @property
    def prompt(self) -> PromptTemplate:
        """RAG prompt template."""
        return PromptTemplate(
            template="""You are a helpful assistant answering questions about a YouTube video.
Answer ONLY from the provided transcript context.
If the context is insufficient or doesn't contain relevant information, say you don't know.

Context from video:
{context}

Question: {question}

Answer:""",
            input_variables=["context", "question"],
        )

    def ingest_transcript(self, transcript: str, video_id: str) -> None:
        """
        Process transcript into vector store and setup retriever.

        Args:
            transcript: Cleaned subtitle text
            video_id: YouTube video ID for metadata
        """
        documents = self._splitter.create_documents(
            texts=[transcript], metadatas=[{"video_id": video_id}]
        )

        vector_store = FAISS.from_documents(
            documents=documents,
            embedding=self.embeddings,
        )

        self._retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": RAGConfig.TOP_K_RESULTS},
        )

        self._build_chain()

    def _build_chain(self) -> None:
        """Build the RAG chain with LCEL."""
        if self._retriever is None:
            raise RuntimeError("Retriever not initialized")

        def format_docs(docs: list[Document]) -> str:
            return "\n\n".join(doc.page_content for doc in docs)

        parallel_chain = RunnableParallel(
            context=self._retriever | RunnableLambda(format_docs),
            question=RunnablePassthrough(),
        )

        self._chain = parallel_chain | self.prompt | self.llm | StrOutputParser()

    def answer(self, question: str) -> str:
        """
        Answer a question using the RAG pipeline.
        """
        if self._chain is None:
            raise RuntimeError("RAG engine not initialized")

        return self._chain.invoke(question)

    @property
    def is_ready(self) -> bool:
        """Check if RAG engine is ready for answering."""
        return self._chain is not None
