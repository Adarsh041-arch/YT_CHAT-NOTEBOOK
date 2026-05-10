"""YouTube Chatbot - Professional SaaS UI."""

import streamlit as st
import requests
from datetime import datetime

from src.config import StreamlitConfig

API_BASE_URL = "http://localhost:8000/api/v1"

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --gradient-start: #6366f1;
        --gradient-end: #8b5cf6;
        --bg-primary: #0f172a;
        --bg-secondary: #1e293b;
        --bg-tertiary: #334155;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --accent: #6366f1;
        --accent-hover: #4f46e5;
        --success: #10b981;
        --error: #ef4444;
        --border: #334155;
    }

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .stApp {
        background: var(--bg-primary);
    }

    .main-header {
        background: linear-gradient(135deg, var(--gradient-start) 0%, var(--gradient-end) 100%);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        text-align: center;
        position: relative;
        overflow: hidden;
    }

    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
        animation: shimmer 3s ease-in-out infinite;
    }

    @keyframes shimmer {
        0%, 100% { transform: translate(-10%, -10%); }
        50% { transform: translate(10%, 10%); }
    }

    .main-header h1 {
        color: white !important;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        position: relative;
        z-index: 1;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }

    .main-header p {
        color: rgba(255,255,255,0.9) !important;
        font-size: 1.1rem;
        margin-top: 0.5rem;
        position: relative;
        z-index: 1;
    }

    .sidebar-section {
        background: var(--bg-secondary);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid var(--border);
    }

    .sidebar-section h3 {
        color: var(--text-primary) !important;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .input-wrapper {
        position: relative;
    }

    .input-wrapper input {
        background: var(--bg-tertiary) !important;
        border: 2px solid var(--border) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
        padding: 0.875rem 1rem !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
    }

    .input-wrapper input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2) !important;
        outline: none !important;
    }

    .input-wrapper input::placeholder {
        color: var(--text-secondary) !important;
    }

    .btn-primary {
        background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end)) !important;
        color: white !important;
        border: none !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        cursor: pointer;
    }

    .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important;
    }

    .btn-secondary {
        background: var(--bg-tertiary) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }

    .btn-secondary:hover {
        background: var(--border) !important;
        border-color: var(--accent) !important;
    }

    .stButton > button {
        border-radius: 10px !important;
        transition: all 0.3s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
    }

    .chat-container {
        background: var(--bg-secondary);
        border-radius: 16px;
        border: 1px solid var(--border);
        padding: 1.5rem;
        height: 500px;
        overflow-y: auto;
    }

    .chat-message {
        padding: 1rem 1.25rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        animation: slideIn 0.3s ease-out;
    }

    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .chat-message.user {
        background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
        color: white;
        margin-left: 3rem;
        border-bottom-right-radius: 4px;
    }

    .chat-message.assistant {
        background: var(--bg-tertiary);
        color: var(--text-primary);
        margin-right: 3rem;
        border-bottom-left-radius: 4px;
        border: 1px solid var(--border);
    }

    .chat-message .role {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
        opacity: 0.8;
    }

    .chat-message.user .role {
        color: rgba(255,255,255,0.9);
    }

    .chat-message.assistant .role {
        color: var(--accent);
    }

    .chat-message p {
        margin: 0;
        line-height: 1.6;
        font-size: 0.95rem;
    }

    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: var(--text-secondary);
    }

    .empty-state .icon {
        font-size: 4rem;
        margin-bottom: 1.5rem;
        opacity: 0.5;
    }

    .empty-state h3 {
        color: var(--text-primary) !important;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }

    .empty-state p {
        font-size: 0.95rem;
        max-width: 400px;
        margin: 0 auto;
    }

    .video-preview {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--border);
    }

    .video-preview img {
        width: 100%;
        border-radius: 12px;
    }

    .session-item {
        background: var(--bg-tertiary);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.875rem 1rem;
        margin-bottom: 0.5rem;
        transition: all 0.3s ease;
        cursor: pointer;
    }

    .session-item:hover {
        border-color: var(--accent);
        transform: translateX(4px);
    }

    .session-item.active {
        border-color: var(--accent);
        background: rgba(99, 102, 241, 0.1);
    }

    .session-item h4 {
        color: var(--text-primary) !important;
        font-size: 0.9rem;
        font-weight: 500;
        margin: 0 0 0.25rem 0;
    }

    .session-item p {
        color: var(--text-secondary) !important;
        font-size: 0.8rem;
        margin: 0;
    }

    .login-container {
        max-width: 420px;
        margin: 4rem auto;
        padding: 2.5rem;
        background: var(--bg-secondary);
        border-radius: 20px;
        border: 1px solid var(--border);
    }

    .login-container h2 {
        color: var(--text-primary) !important;
        text-align: center;
        margin-bottom: 0.5rem !important;
    }

    .login-container p {
        color: var(--text-secondary) !important;
        text-align: center;
        margin-bottom: 2rem !important;
    }

    .divider {
        border: none;
        height: 1px;
        background: var(--border);
        margin: 1.5rem 0;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 100px;
        font-size: 0.85rem;
        font-weight: 500;
    }

    .status-badge.success {
        background: rgba(16, 185, 129, 0.1);
        color: var(--success);
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .status-badge.error {
        background: rgba(239, 68, 68, 0.1);
        color: var(--error);
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: currentColor;
    }

    .chat-input-wrapper {
        margin-top: 1rem;
    }

    .chat-input-wrapper .stChatInput input {
        background: var(--bg-tertiary) !important;
        border: 2px solid var(--border) !important;
        border-radius: 24px !important;
        color: var(--text-primary) !important;
        padding: 1rem 1.25rem !important;
        font-size: 1rem !important;
    }

    .chat-input-wrapper .stChatInput input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: var(--bg-tertiary);
        padding: 0.5rem;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: var(--accent) !important;
        color: white !important;
    }

    .video-caption {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1rem;
        background: var(--bg-tertiary);
        border-radius: 8px;
        margin-top: 0.75rem;
    }

    .video-caption code {
        color: var(--accent) !important;
        font-size: 0.85rem;
    }

    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-primary);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-secondary);
    }
</style>
""", unsafe_allow_html=True)


def get_headers():
    headers = {}
    if st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    return headers


def call_api(endpoint: str, method: str = "GET", body: dict = None, is_form: bool = False):
    url = f"{API_BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, headers=get_headers(), timeout=120)
        elif method == "POST":
            if is_form:
                response = requests.post(url, data=body, headers=get_headers(), timeout=120)
            else:
                response = requests.post(url, json=body, headers=get_headers(), timeout=120)
        elif method == "DELETE":
            response = requests.delete(url, headers=get_headers())

        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to API. Make sure FastAPI server is running on port 8000."}
    except requests.exceptions.HTTPError as e:
        try:
            return {"error": e.response.json().get("detail", str(e))}
        except:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def stream_chat(video_id: str, question: str, session_id: str = None):
    url = f"{API_BASE_URL}/chat"
    payload = {"video_id": video_id, "question": question}
    if session_id:
        payload["session_id"] = session_id

    try:
        with requests.post(url, json=payload, headers=get_headers(), stream=True, timeout=120) as r:
            r.raise_for_status()

            new_session_id = r.headers.get("X-Session-ID")
            if new_session_id:
                st.session_state.session_id = new_session_id

            for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    yield chunk
    except Exception as e:
        yield f"\n\nError connecting to API: {str(e)}"


def get_video_thumbnail(video_id: str) -> str:
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"


def load_session(session_info):
    with st.spinner("Loading session..."):
        messages = call_api(f"/sessions/{session_info['id']}/messages")
        if "error" not in messages:
            st.session_state.session_id = session_info["id"]
            st.session_state.current_video = session_info["video_id"]
            history = []
            current_q = ""
            for msg in messages:
                if msg["role"] == "user":
                    current_q = msg["content"]
                else:
                    history.append((current_q, msg["content"]))
            st.session_state.chat_history = history
            st.rerun()


def render_login():
    st.markdown("""
    <div class="login-container">
        <h2>Welcome Back</h2>
        <p>Sign in to continue with your video chats</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Sign In", "Create Account"])

        with tab1:
            with st.form("login_form", clear_on_submit=False):
                st.text_input("Username", key="login_user", placeholder="Enter your username")
                st.text_input("Password", key="login_pass", type="password", placeholder="Enter your password")

                if st.form_submit_button("Sign In", use_container_width=True, type="primary"):
                    user = st.session_state.login_user
                    password = st.session_state.login_pass
                    res = call_api("/auth/login", method="POST", body={"username": user, "password": password}, is_form=True)
                    if "error" in res:
                        st.error(res["error"])
                    else:
                        st.session_state.token = res["access_token"]
                        st.rerun()

        with tab2:
            with st.form("register_form", clear_on_submit=False):
                st.text_input("Username", key="reg_user", placeholder="Min. 3 characters")
                st.text_input("Password", key="reg_pass", type="password", placeholder="Min. 6 characters")

                if st.form_submit_button("Create Account", use_container_width=True):
                    user = st.session_state.reg_user
                    password = st.session_state.reg_pass
                    res = call_api("/auth/register", method="POST", body={"username": user, "password": password})
                    if "error" in res:
                        st.error(res["error"])
                    else:
                        st.success("Account created! Please sign in.")


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div class="main-header" style="padding: 1rem; margin-bottom: 1.5rem;">
            <h1 style="font-size: 1.5rem;">YTChatBot</h1>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown('<h3><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg> Load Video</h3>', unsafe_allow_html=True)

            video_id_input = st.text_input(
                "YouTube Video ID",
                placeholder="dQw4w9WgXcQ",
                label_visibility="collapsed",
            )

            col1, col2 = st.columns(2)
            with col1:
                process_btn = st.button("Load Video", use_container_width=True, type="primary")
            with col2:
                reset_btn = st.button("Reset", use_container_width=True)

            return video_id_input, process_btn, reset_btn

        if st.session_state.current_video:
            with st.container():
                st.markdown('<h3><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect><line x1="7" y1="2" x2="7" y2="22"></line><line x1="17" y1="2" x2="17" y2="22"></line><line x1="2" y1="12" x2="22" y2="12"></line><line x1="2" y1="7" x2="7" y2="7"></line><line x1="2" y1="17" x2="7" y2="17"></line><line x1="17" y1="17" x2="22" y2="17"></line><line x1="17" y1="7" x2="22" y2="7"></line></svg> Video Preview</h3>', unsafe_allow_html=True)
                st.image(
                    get_video_thumbnail(st.session_state.current_video),
                    use_container_width=True,
                )
                st.markdown(f"""
                <div class="video-caption">
                    <span>Video ID:</span>
                    <code>{st.session_state.current_video}</code>
                </div>
                """, unsafe_allow_html=True)

                health = call_api("/health")
                if health and "error" not in health:
                    count = health.get('videos_loaded', 0)
                    st.markdown(f"""
                    <span class="status-badge success">
                        <span class="status-dot"></span>
                        Ready · {count} video(s) loaded
                    </span>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <span class="status-badge success">
                        <span class="status-dot"></span>
                        Ready to chat
                    </span>
                    """, unsafe_allow_html=True)

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        with st.container():
            st.markdown('<h3><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg> Chat History</h3>', unsafe_allow_html=True)
            sessions = call_api("/sessions")
            if isinstance(sessions, list) and sessions:
                for s in sessions:
                    is_active = s['id'] == st.session_state.session_id
                    btype = "primary" if is_active else "secondary"
                    if st.button(f"📝 {s['title']} ({s['message_count']} msgs)", key=f"sess_{s['id']}", use_container_width=True, type=btype):
                        load_session(s)
            else:
                st.caption("No past sessions yet. Start a conversation!")

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        if st.button("Logout", use_container_width=True, type="secondary"):
            st.session_state.token = None
            st.session_state.session_id = None
            st.session_state.current_video = None
            st.session_state.chat_history = []
            st.rerun()


def render_chat(video_id_input, process_btn, reset_btn):
    st.markdown('<h2 style="color: var(--text-primary); margin-bottom: 1.5rem;">Conversation</h2>', unsafe_allow_html=True)

    chat_container = st.container(height=500)

    if process_btn and video_id_input:
        with st.spinner("Processing video..."):
            result = call_api("/process", method="POST", body={"video_id": video_id_input})

            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.session_state.current_video = video_id_input
                st.session_state.chat_history = []
                st.session_state.session_id = None
                st.rerun()

    if reset_btn:
        st.session_state.current_video = None
        st.session_state.chat_history = []
        st.session_state.session_id = None
        st.rerun()

    with chat_container:
        if not st.session_state.chat_history:
            st.markdown("""
            <div class="empty-state">
                <div class="icon">💬</div>
                <h3>Start a conversation</h3>
                <p>Load a YouTube video and ask questions about its content. The AI will analyze the video to provide accurate answers.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for q, a in st.session_state.chat_history:
                with st.chat_message("user"):
                    st.write(q)
                with st.chat_message("assistant"):
                    st.write(a)

    if st.session_state.current_video:
        question = st.chat_input("Ask a question about the video...")
        if question:
            with chat_container:
                with st.chat_message("user"):
                    st.write(question)

                with st.chat_message("assistant"):
                    response_stream = stream_chat(
                        st.session_state.current_video,
                        question,
                        st.session_state.session_id
                    )
                    full_response = st.write_stream(response_stream)

            st.session_state.chat_history.append((question, full_response))


def main():
    st.set_page_config(
        page_title=StreamlitConfig.APP_TITLE,
        page_icon="🎬",
        layout="wide",
    )

    if "token" not in st.session_state:
        st.session_state.token = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "current_video" not in st.session_state:
        st.session_state.current_video = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = None

    if not st.session_state.token:
        render_login()
        return

    video_id_input, process_btn, reset_btn = render_sidebar()

    col_sidebar, col_main = st.columns([1, 3], gap="large")

    with col_main:
        render_chat(video_id_input, process_btn, reset_btn)


if __name__ == "__main__":
    main()
