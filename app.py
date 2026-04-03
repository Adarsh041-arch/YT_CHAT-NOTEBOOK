"""YouTube Chatbot - Streamlit UI (calls FastAPI backend)."""

import streamlit as st
import requests

from src.config import StreamlitConfig

API_BASE_URL = "http://localhost:8000/api/v1"


def call_api(endpoint: str, method: str = "GET", body: dict = None):
    """Make API call to FastAPI backend."""
    url = f"{API_BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, timeout=120)
        elif method == "POST":
            response = requests.post(url, json=body, timeout=120)
        elif method == "DELETE":
            response = requests.delete(url)

        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError:
        return {
            "error": "Cannot connect to API. Make sure FastAPI server is running on port 8000."
        }
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Please try again."}
    except requests.exceptions.HTTPError as e:
        try:
            return {"error": e.response.json().get("detail", str(e))}
        except:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def get_video_thumbnail(video_id: str) -> str:
    """Get YouTube video thumbnail URL."""
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"


def render_message(role: str, content: str, timestamp: str = ""):
    """Render a chat message with professional styling."""
    if role == "user":
        bubble_class = "user-bubble"
        align = "right"
        avatar = "👤"
    else:
        bubble_class = "assistant-bubble"
        align = "left"
        avatar = "🤖"

    st.markdown(
        f"""
    <div style="display: flex; justify-content: {align}; margin: 10px 0;">
        <div style="max-width: 75%;">
            <div style="display: flex; align-items: center; margin-bottom: 5px; justify-content: {"flex-end" if align == "right" else "flex-start"};">
                <span style="font-size: 0.85em; color: #888; margin-{("right" if align == "right" else "left")}: 8px;">{timestamp}</span>
                <span style="font-size: 1.2em;">{avatar}</span>
            </div>
            <div class="{bubble_class}" style="padding: 12px 16px; border-radius: 16px; {"border-bottom-right-radius: 4px" if align == "right" else "border-bottom-left-radius: 4px"};">
                <p style="margin: 0; line-height: 1.5; font-size: 0.95em;">{content}</p>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title=StreamlitConfig.APP_TITLE,
        page_icon="🎬",
        layout="wide",
    )

    st.markdown(
        """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    * {{
        font-family: 'Inter', sans-serif;
    }}
    
    .stApp {{
        background-color: #f8fafc;
    }}
    
    .header-container {{
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 20px 30px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }}
    
    .header-title {{
        color: white;
        font-size: 1.8em;
        font-weight: 600;
        margin: 0;
    }}
    
    .header-subtitle {{
        color: #94a3b8;
        font-size: 0.9em;
        margin: 5px 0 0 0;
    }}
    
    .user-bubble {{
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
        color: white;
    }}
    
    .assistant-bubble {{
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        color: white;
    }}
    
    .chat-container {{
        background: white;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        min-height: 500px;
        max-height: 600px;
        overflow-y: auto;
    }}
    
    .sidebar-card {{
        background: white;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 16px;
    }}
    
    .video-thumbnail {{
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}
    
    .status-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: 500;
    }}
    
    .status-success {{
        background: #dcfce7;
        color: #166534;
    }}
    
    .status-warning {{
        background: #fef9c3;
        color: #854d0e;
    }}
    
    .input-area {{
        background: white;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    
    div[data-testid="stMainBlockContainer"] {{
        padding-top: 2rem;
    }}
    
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {{
        border: 2px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px;
        font-size: 0.95em;
    }}
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: #dc2626;
        box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
    }}
    
    .stButton > button {{
        border-radius: 10px;
        font-weight: 500;
        transition: all 0.2s ease;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}
    
    .footer {{
        text-align: center;
        color: #94a3b8;
        font-size: 0.8em;
        padding: 20px 0;
    }}
    
    .empty-state {{
        text-align: center;
        padding: 60px 20px;
        color: #64748b;
    }}
    
    .empty-state-icon {{
        font-size: 3em;
        margin-bottom: 16px;
    }}
    
    ::-webkit-scrollbar {{
        width: 6px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: #f1f5f9;
        border-radius: 3px;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: #cbd5e1;
        border-radius: 3px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: #94a3b8;
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "current_video" not in st.session_state:
        st.session_state.current_video = None

    col_sidebar, col_main = st.columns([1, 3], gap="large")

    with col_sidebar:
        st.markdown(
            """
        <div class="header-container">
            <h1 class="header-title">🎬 YTChatBot</h1>
            <p class="header-subtitle">Ask questions about YouTube videos</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        with st.container():
            st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
            st.subheader("📹 Video Input")

            video_id_input = st.text_input(
                "YouTube Video ID",
                placeholder="dQw4w9WgXcQ",
                help="Find the video ID in the URL after 'v='",
            )

            col1, col2 = st.columns(2)
            with col1:
                process_btn = st.button(
                    "▶️ Load Video", type="primary", use_container_width=True
                )
            with col2:
                reset_btn = st.button("🔄 Reset", use_container_width=True)

            if st.session_state.current_video:
                st.markdown(
                    f'<span class="status-badge status-success">✅ Video Loaded</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<span class="status-badge status-warning">⚠️ No Video</span>',
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.current_video:
            with st.container():
                st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
                st.subheader("📺 Preview")
                st.image(
                    get_video_thumbnail(st.session_state.current_video),
                    width=280,
                    use_container_width=True,
                )
                st.caption(f"Video ID: `{st.session_state.current_video}`")

                health = call_api("/health")
                if health and health.get("videos_loaded", 0) > 0:
                    st.success(
                        f"Ready to chat! ({health['videos_loaded']} video(s) in memory)"
                    )

                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(
            '<p class="footer">Powered by Gemini + LangChain</p>',
            unsafe_allow_html=True,
        )

    with col_main:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)

        st.subheader("💬 Conversation")

        if not st.session_state.chat_history:
            st.markdown(
                f"""
            <div class="empty-state">
                <div class="empty-state-icon">💭</div>
                <h3>Start a conversation</h3>
                <p>Load a YouTube video and ask questions about its content</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            for q, a in st.session_state.chat_history:
                render_message("user", q)
                render_message("assistant", a)

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="input-area">', unsafe_allow_html=True)

        col_input, col_btn = st.columns([4, 1])

        with col_input:
            if st.session_state.current_video:
                question = st.text_area(
                    "Ask a question",
                    placeholder="Type your question here...",
                    height=60,
                    label_visibility="collapsed",
                    key="question_input",
                )
            else:
                st.text_area(
                    "Ask a question",
                    placeholder="Load a video first to start chatting...",
                    height=60,
                    disabled=True,
                    label_visibility="collapsed",
                )
                question = ""

        with col_btn:
            st.write("")
            send_btn = st.button(
                "Send",
                type="primary",
                use_container_width=True,
                disabled=not st.session_state.current_video,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    if process_btn and video_id_input:
        with st.spinner("🔍 Processing video..."):
            result = call_api(
                "/process", method="POST", body={"video_id": video_id_input}
            )

            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.session_state.current_video = video_id_input
                st.session_state.chat_history = []
                st.success(
                    f"Video loaded successfully! Language: {result.get('language', 'unknown')}"
                )
                st.rerun()

    if reset_btn:
        if st.session_state.current_video:
            call_api(f"/videos/{st.session_state.current_video}", method="DELETE")
        st.session_state.current_video = None
        st.session_state.chat_history = []
        st.rerun()

    if send_btn and question and st.session_state.current_video:
        with st.spinner("🤔 Thinking..."):
            result = call_api(
                "/chat",
                method="POST",
                body={
                    "video_id": st.session_state.current_video,
                    "question": question,
                },
            )

            if "error" in result:
                answer = f"Error: {result['error']}"
            else:
                answer = result.get("answer", "No response received.")

        st.session_state.chat_history.append((question, answer))
        st.rerun()


if __name__ == "__main__":
    main()
