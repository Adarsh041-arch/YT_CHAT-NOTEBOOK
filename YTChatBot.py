import streamlit as st
import yt_dlp
import re
import requests
from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnableLambda, RunnablePassthrough
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

load_dotenv()
parser = StrOutputParser()

st.title("Youtube Chatbot")

video_id = st.text_input("YouTube Video ID", placeholder="Enter video ID...")

# 1️⃣ SUBMIT BUTTON → PROCESS VIDEO
if st.button("Submit"):

    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "hi"],
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    subs = info.get("requested_subtitles")
    if not subs:
        st.error("No subtitles found!")
        st.stop()

    # pick any available subtitle
    lang = next(iter(subs))
    subtitle_url = subs[lang]["url"]

    transcript = requests.get(subtitle_url).text

    # clean subtitles
    def clean_vtt(vtt_text):
        vtt_text = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3} --> .*", "", vtt_text)
        vtt_text = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", vtt_text)
        vtt_text = re.sub(r"</?c>", "", vtt_text)
        vtt_text = re.sub(r"\s+", " ", vtt_text.replace("\n", " "))
        return vtt_text.strip()

    transcript = clean_vtt(transcript)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    # create_documents accepts a list[str] and returns List[Document]
    chunks = splitter.create_documents([transcript])

    # Vector DB (use Google Generative AI embeddings)
    embeddings = GoogleGenerativeAIEmbeddings(model='gemini-embedding-001')
    vector_store = FAISS.from_documents(
        chunks,
        embeddings
    )

    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={'k': 4})

    # Save retriever in session_state
    st.session_state["retriever"] = retriever

    # LLM and prompt
    llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash', temperature=0.3)

    prompt = PromptTemplate(
        template="""
        You are a helpful assistant.
        Answer ONLY from the provided transcript context.
        If the context is insufficient, say you don't know.

        {context}

        Question: {question}
        """,
        input_variables=['context', 'question']
    )

    st.session_state["llm"] = llm
    st.session_state["prompt"] = prompt

    st.success("Video processed! Now ask your question.")


# 2️⃣ CHAT SECTION (ALWAYS VISIBLE AFTER SUBMIT)
Input_quest = st.text_input("Ask your question", placeholder="Ask your doubt !")

if st.button("Chat"):

    # check if video is processed
    if "retriever" not in st.session_state:
        st.error("Please submit a video first!")
        st.stop()

    retriever = st.session_state["retriever"]
    llm = st.session_state["llm"]
    prompt = st.session_state["prompt"]

    def format_docs(retrieved_docs):
        return "\n\n".join(doc.page_content for doc in retrieved_docs)

    parallel_chain = RunnableParallel({
        "context": retriever | RunnableLambda(format_docs),
        "question": RunnablePassthrough()
    })

    main_chain = parallel_chain | prompt | llm | parser

    answer = main_chain.invoke(Input_quest)

    st.write(answer)
