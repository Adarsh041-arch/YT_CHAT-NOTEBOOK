# YTChatBot

AI-powered YouTube video chatbot that lets you ask questions about video content using RAG (Retrieval-Augmented Generation).

## Features

- **Video Processing**: Extract subtitles from YouTube videos automatically
- **Playlist Support**: Process entire YouTube playlists at once
- **RAG Chat**: Ask questions about video content with AI-powered answers
- **Streaming Responses**: Real-time AI response streaming
- **User Authentication**: Secure JWT-based authentication
- **Session Management**: Save and load chat sessions

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite
- **Database**: SQLite
- **Vector Store**: FAISS
- **LLM**: OpenRouter API (configurable models)
- **Embeddings**: Ollama (nomic-embed-text)
- **Video Processing**: yt-dlp

## Project Structure

```
YTChatBot/
├── api/               # FastAPI routes and models
├── src/               # Core business logic
│   ├── config.py      # Configuration settings
│   ├── rag_engine.py  # RAG pipeline
│   ├── video_processor.py  # YouTube video processing
│   └── database.py   # Database models
├── frontend/          # React frontend
├── data/              # Database and FAISS indexes
├── main.py            # FastAPI entry point
└── .env               # Environment variables
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama (for embeddings)
- OpenRouter API key

## Setup

### 1. Clone and Install Dependencies

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# OpenRouter API (required for LLM)
OPENROUTER_API_KEY=your-api-key-here
```

### 3. Start Ollama (for embeddings)

```bash
ollama serve
ollama pull nomic-embed-text
```

### 4. Run the Application

**Backend:**
```bash
python main.py
# API runs at http://localhost:8000
```

**Frontend:**
```bash
cd frontend
npm run dev
# App runs at http://localhost:5173
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login and get token |
| POST | `/process` | Process single video |
| POST | `/playlist/stream` | Process playlist (streaming) |
| GET | `/sessions` | Get user sessions |
| POST | `/chat` | Chat with video (streaming) |

## Configuration

Edit `src/config.py` to customize:

```python
class LLMConfig:
    MODEL: str = "openai/gpt-5.2"  # LLM model
    EMBEDDING_MODEL: str = "nomic-embed-text:latest"  # Embeddings

class RAGConfig:
    CHUNK_SIZE: int = 300  # Text chunk size
    TOP_K_RESULTS: int = 2  # Number of context chunks
```

## Usage

1. Open the frontend at http://localhost:5173
2. Register/Login with username and password
3. Enter a YouTube video URL or playlist URL
4. Wait for processing to complete
5. Ask questions about the video content

## License

MIT