"""RAG (Retrieval-Augmented Generation) engine for Q&A."""

import os
from typing import Optional, AsyncGenerator

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import (
    Runnable,
    RunnableParallel,
    RunnableLambda,
    RunnablePassthrough,
)
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

from .config import RAGConfig, LLMConfig, StorageConfig


class RAGEngine:
    """RAG engine for processing transcripts and answering questions."""

    def __init__(self) -> None:
        self._embeddings: Optional[OllamaEmbeddings] = None
        self._llm: Optional[ChatOpenAI] = None
        self._retriever = None
        self._chain: Optional[Runnable] = None
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=RAGConfig.CHUNK_SIZE,
            chunk_overlap=RAGConfig.CHUNK_OVERLAP,
        )

    @property
    def embeddings(self) -> OllamaEmbeddings:
        """Lazy initialization of embeddings model."""
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(
                model=LLMConfig.EMBEDDING_MODEL
            )
        return self._embeddings

    @property
    def llm(self) -> ChatOpenAI:
        """Lazy initialization of chat model."""
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

    def load_or_ingest_transcript(self, transcript: str, video_id: str) -> None:
        """
        Load existing FAISS index or process transcript into vector store.
        """
        index_path = str(StorageConfig.FAISS_DIR / video_id)
        
        if os.path.exists(index_path):
            vector_store = FAISS.load_local(
                folder_path=index_path, 
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            documents = self._splitter.create_documents(
                texts=[transcript], metadatas=[{"video_id": video_id}]
            )
            vector_store = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings,
            )
            vector_store.save_local(index_path)

        self._retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": RAGConfig.TOP_K_RESULTS},
        )

        self._build_chain()

    def _build_chain(self) -> None:
        """Build the RAG chain with conversational memory."""
        if self._retriever is None:
            raise RuntimeError("Retriever not initialized")

        contextualize_q_system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
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
            "1. **Use the Video Context**: Base your primary answer on the provided video context below. "
            "IMPORTANT: The context contains timestamps in the format [HH:MM:SS]. "
            "When pulling facts from the video, you MUST cite the exact timestamps inline.\n"
            "2. **Avoid Robotic Phrasing**: Do NOT use phrases like 'as per the transcript', 'according to the provided text', or 'the transcript says'. You may use natural phrasing like 'based on the video' or simply state the facts directly.\n"
            "3. **General Knowledge Fallback**: If the video context does not provide sufficient detail to fully answer the query, first provide whatever information IS available in the video. Then, you may provide your own general knowledge or suggestions to fully answer the user, BUT you MUST explicitly state that this additional information is a general suggestion and is not covered in the video.\n\n"
            "### Video Context:\n"
            "{context}"
        )
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])

        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        self._chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    def answer(self, question: str, chat_history: list = None) -> str:
        """Answer a question using the RAG pipeline."""
        if self._chain is None:
            raise RuntimeError("RAG engine not initialized")

        if chat_history is None:
            chat_history = []
            
        result = self._chain.invoke({
            "input": question,
            "chat_history": chat_history
        })
        return result["answer"]

    async def aanswer_stream(self, question: str, chat_history: list = None) -> AsyncGenerator[str, None]:
        """Stream the answer asynchronously."""
        if self._chain is None:
            raise RuntimeError("RAG engine not initialized")

        if chat_history is None:
            chat_history = []

        try:
            async for chunk in self._chain.astream({
                "input": question,
                "chat_history": chat_history
            }):
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
        """Check if RAG engine is ready for answering."""
        return self._chain is not None
