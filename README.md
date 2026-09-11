# YTChatBot

AI-powered YouTube video and playlist chatbot that lets you ask questions about video content using RAG (Retrieval-Augmented Generation). It automatically extracts subtitles/transcripts, splits them into logical chunks, indexes them into a high-performance vector store, and provides context-aware answers to user queries with real-time streaming — enhanced with **interactive visualizations**, **playlist-level cross-video analysis**, and **LangSmith observability tracing**.

---

## Features

### Core
- **Video Processing**: Automatically extracts transcripts from YouTube videos using video IDs or URLs.
- **Playlist Support**: Process entire YouTube playlists sequentially, streaming the indexing status of each video in real-time.
- **Advanced RAG Chat**: Ask context-sensitive questions about video content using a multi-turn conversation memory.
- **Streaming Responses**: Real-time server-sent events (SSE) for AI answer generation.

### Intelligent Visualizations *(New)*
- **Auto-Classification**: An LLM classifier automatically detects whether a user's query would benefit from a visualization (chart, graph, diagram, or custom simulation) — no manual toggling required.
- **D3.js Charts**: Interactive bar, line, scatter, and pie charts rendered with D3.js for numeric/statistical queries.
- **D3.js Graphs**: Force-directed, tree, and radial network graphs for relationship and hierarchy queries.
- **Mermaid Diagrams**: Flowcharts and sequence diagrams generated from Mermaid syntax for architecture and process-flow queries.
- **p5.js Custom Simulations**: Fully sandboxed, auto-playing canvas animations for algorithm walkthroughs, physical simulations, and step-by-step process explanations (e.g., backpropagation, sorting algorithms).
- **AST-Based Code Validation**: Generated p5.js code is parsed and validated against a strict AST-level security sandbox (forbidden globals, import blocking, structure checks) before execution.
- **Auto-Regeneration**: If a visualization fails client-side validation, the backend automatically retries with error feedback for self-healing spec generation.

### Playlist-Level RAG *(New)*
- **Cross-Video Querying**: Ask questions that span across all videos in a playlist, with answers citing specific video positions.
- **Relation Graph**: Automatically builds a cosine-similarity-based relation graph between playlist videos using transcript embeddings, enabling relationship-aware answers.
- **Relation-Aware Answers**: When a user asks comparative or relationship questions (e.g., "How do these videos relate?"), the system enriches context with the relation graph and neighboring video transcripts.

### Observability & Tracing *(New)*
- **LangSmith Integration**: Centralized `@traceable` decorator for full pipeline tracing — every embedding call, retrieval, classification, and generation step is logged as a LangSmith run.
- **Embedding Tracing**: Monkey-patched SentenceTransformer `.encode()` calls appear as nested embedding runs in the trace tree.

### Multi-Provider LLM Support *(New)*
- **OpenRouter** (default): Access hundreds of models (GPT-4o-mini, Claude, Llama, etc.) via a single API key.
- **NVIDIA NIM**: Direct integration with NVIDIA's hosted inference (Llama 3.1, etc.).
- **Google Gemini**: Native `langchain-google-genai` integration for Gemini models.
- Configurable via a single `LLM_PROVIDER` environment variable.

### UI Enhancements *(New)*
- **Embedded YouTube Player**: Resizable, floating YouTube player with iframe API integration — supports seeking to specific timestamps referenced in chat answers.
- **Skeleton Loaders**: Animated shimmer placeholders for video cards, session cards, and chat bubbles during loading states.
- **Visualization Error Boundaries**: React error boundaries around all visualization components to gracefully handle render failures without crashing the chat.

### Infrastructure
- **MongoDB Integration**: Asynchronous database for storing user registrations, credentials (secured with bcrypt), chat sessions, message histories, processed video logs, playlist relation graphs, and visualization cache/logs.
- **Pinecone Vector Database**: High-speed, cloud-native vector similarity index for storing embeddings with namespace isolation per YouTube video ID.
- **JWT Authentication**: Secure user login and authorization logic.

---

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: MongoDB (via `motor` asynchronous driver)
- **Vector Database**: Pinecone
- **RAG Orchestration**: LangChain & LangChain-OpenAI & LangChain-Google-GenAI
- **Embeddings**: SentenceTransformers (`all-MiniLM-L6-v2` — 384-dimensional dense vectors)
- **Visualization Classifier**: LLM-powered auto-classification (chart / graph / diagram / custom)
- **Observability**: LangSmith (`@traceable` decorator for full pipeline tracing)
- **Authentication**: JWT (JSON Web Tokens) & Passlib (bcrypt)
- **Video Extraction**: yt-dlp & youtube-transcript-api

### Frontend
- **Framework**: React + Vite (JavaScript)
- **Styling**: TailwindCSS & Vanilla CSS
- **Visualizations**: D3.js (charts & graphs), Mermaid.js (diagrams), p5.js (simulations)
- **Code Validation**: Acorn (AST parsing for p5.js sandbox validation)
- **HTTP Client**: Axios (with token interceptors for auth)
- **Deployment**: Vercel-ready build output

---

## Project Structure

```
YTChatBot/
├── backend/                       # FastAPI Backend Service
│   ├── api/                       # API endpoints and validation models
│   │   ├── models.py              # Pydantic schemas (requests, responses, viz specs)
│   │   ├── routes.py              # Routes (Auth, Video, Playlists, Chat, Visualizations)
│   │   └── viz_utils.py           # [NEW] Visualization classifier & spec generator
│   ├── src/                       # Core Business Logic
│   │   ├── auth.py                # Password hashing & JWT generation
│   │   ├── config.py              # Global config (LLM, RAG, Viz, Storage settings)
│   │   ├── database.py            # MongoDB client & operations (incl. playlist/viz collections)
│   │   ├── playlist_rag.py        # [NEW] Playlist-level RAG engine with relation graphs
│   │   ├── rag_engine.py          # RAG pipeline with LangChain & Pinecone indexer
│   │   ├── tracing.py             # [NEW] LangSmith @traceable decorator & embedding tracer
│   │   └── video_processor.py     # YouTube transcript retrieval utilities
│   ├── data/                      # Local directory for cached assets
│   ├── main.py                    # FastAPI server entry point
│   ├── requirements.txt           # Python backend packages
│   └── runtime.txt                # Python runtime version
├── frontend/                      # React Frontend Application
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.jsx           # Main chat interface (with viz rendering)
│   │   │   ├── Sidebar.jsx        # Sidebar navigation
│   │   │   ├── Skeleton.jsx       # [NEW] Skeleton loading placeholders
│   │   │   ├── YouTubePlayer.jsx  # [NEW] Embedded resizable YouTube player
│   │   │   └── visualizations/    # [NEW] Visualization component library
│   │   │       ├── D3Chart.jsx    #   Bar, line, scatter, pie charts (D3.js)
│   │   │       ├── D3Graph.jsx    #   Force/tree/radial network graphs (D3.js)
│   │   │       ├── MermaidDiagram.jsx  # Flowchart & sequence diagrams (Mermaid)
│   │   │       ├── P5Custom.jsx   #   Custom sandboxed p5.js animations
│   │   │       ├── P5Simulation.jsx#   Step-based algorithm simulations (p5.js)
│   │   │       ├── VisualizationRenderer.jsx # Viz type router/dispatcher
│   │   │       └── VizErrorBoundary.jsx # React error boundary for viz failures
│   │   ├── context/               # React contexts (e.g. Authentication status)
│   │   ├── hooks/                 # Custom hooks
│   │   ├── services/              # API client handlers
│   │   │   └── api.js             # Axios client (updated with viz & playlist endpoints)
│   │   ├── utils/
│   │   │   └── astValidator.js    # [NEW] AST-level p5.js code sandbox validator
│   │   ├── App.jsx                # App root with routing
│   │   ├── index.css              # Global styles
│   │   └── main.jsx               # Entry point
│   ├── package.json               # Node dependencies (added d3, mermaid, p5, acorn)
│   └── vite.config.js             # Vite config
├── .env                           # Application environment variables (Git-ignored)
└── .env.example                   # Sample environment template file
```

---

## Prerequisites

Before starting, ensure you have:
- **Python 3.11+**
- **Node.js 18+**
- A **MongoDB** database instance (local or [MongoDB Atlas Cloud](https://www.mongodb.com/cloud/atlas))
- A **Pinecone** account with an active API Key and Index ([Pinecone Console](https://console.pinecone.io/))
- **One of the following LLM providers**:
  - An **OpenRouter API Key** ([OpenRouter](https://openrouter.ai/)) — *default provider*
  - An **NVIDIA NIM API Key** ([NVIDIA](https://build.nvidia.com/))
  - A **Google API Key** with Gemini access ([Google AI Studio](https://aistudio.google.com/))

---

## Setup & Local Installation

### 1. Clone the Repository
Clone the project to your local directory and navigate into it:
```bash
git clone <repository-url>
cd YTChatBot
```

### 2. Configure Environment Variables
Copy the environment template from the root of the project and update the values:
```bash
cp .env.example .env
```
Fill in the credentials in `.env` as described in the [Environment Variables](#environment-variables) section below.

### 3. Backend Setup
Navigate to the `backend/` directory, create a virtual environment, activate it, and install python dependencies:

**On Windows:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**On macOS/Linux:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Frontend Setup
Navigate to the `frontend/` directory and install dependencies:
```bash
cd ../frontend
npm install
```

---

## Running the Application Locally

### 1. Run the Backend Server
Start the FastAPI server using Uvicorn (make sure your virtual environment is active in the `backend/` directory):
```bash
cd backend
python main.py
```
The backend API documentation will be available at `http://localhost:8000/docs`.

### 2. Run the Frontend Dev Server
In a separate terminal, navigate to the `frontend/` directory and start the Vite development server:
```bash
cd frontend
npm run dev
```
Open your browser and navigate to `http://localhost:5173`.

---

## Environment Variables

Configure these settings in the root `.env` file:

```env
# --- LLM Provider Selection ---
# Choose provider: "openrouter" (default), "nvidia", or "gemini"
LLM_PROVIDER=openrouter

# --- OpenRouter (default provider) ---
OPENROUTER_API_KEY=your_openrouter_api_key_here
LLM_MODEL=openai/gpt-4o-mini

# --- NVIDIA NIM (alternative provider) ---
NVIDIA_API_KEY=your_nvidia_api_key_here
NVIDIA_MODEL=meta/llama-3.1-8b-instruct

# --- Google Gemini (alternative provider) ---
GOOGLE_API_KEY=your_google_api_key_here

# --- Database Config ---
# Connection URI for your MongoDB cluster (Atlas or Local)
MONGODB_URL=mongodb+srv://<username>:<password>@cluster.mongodb.net/yt_chatbot?retryWrites=true&w=majority
# Name of the database to use
DATABASE_NAME=yt_chatbot

# --- Vector Database Config (Pinecone) ---
# Pinecone API Key
PINECONE_API_KEY=your_pinecone_api_key_here
# Name of the target Pinecone index (e.g. ytchatbot)
PINECONE_INDEX_NAME=ytchatbot
# Pinecone host URL (can be retrieved from the index details page)
PINECONE_HOST=https://your-index-url.pinecone.io
# Model code name for embeddings
PINECONE_EMBEDDING_MODEL=all-MiniLM-L6-v2

# --- Security Config ---
# Secret key for signing JWT auth tokens
SECRET_KEY=your_super_secret_jwt_key_here
```

Configure these settings in `frontend/.env` file:
```env
VITE_API_URL=http://localhost:8000/api/v1
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/register` | Register a new user |
| `POST` | `/api/v1/login` | Login and receive JWT token |

### Video Processing
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/process` | Process a YouTube video transcript |
| `GET` | `/api/v1/health` | Health check with loaded video count |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chat` | Chat about a processed video (SSE streaming) |
| `GET` | `/api/v1/sessions` | List user's chat sessions |
| `GET` | `/api/v1/sessions/{id}/messages` | Get messages for a session |
| `DELETE`| `/api/v1/sessions/{id}` | Delete a chat session |

### Playlists
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/playlist/process` | Process all videos in a playlist |
| `POST` | `/api/v1/playlist/load` | Load & index a playlist with relation graph |
| `POST` | `/api/v1/playlist/query` | Query across all playlist videos (SSE) |
| `GET` | `/api/v1/playlists` | List user's processed playlists |

### Visualizations
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/visualize` | Classify query & generate visualization spec |
| `POST` | `/api/v1/visualize/regenerate` | Regenerate a failed visualization with error feedback |
| `POST` | `/api/v1/visualize/log-validation` | Log client-side validation results |

---

## Visualization Pipeline

The visualization system works through a multi-stage pipeline:

```
User Query → LLM Classifier → Category Decision
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
         "none"              "chart/graph/diagram"       "custom"
      (text only)           (JSON spec generation)    (p5.js code gen)
                                    │                       │
                              Pydantic Validation     AST Sandbox Check
                                    │                       │
                              D3.js / Mermaid          p5.js Canvas
                               Rendering              Rendering
```

1. **Classification**: The classifier LLM determines if a visualization is appropriate and selects the category.
2. **Spec Generation**: A second LLM call generates either a structured JSON spec (chart/graph/diagram) or raw p5.js code (custom).
3. **Validation**: JSON specs are validated with Pydantic models; p5.js code is parsed with Acorn and checked against a strict AST-level security sandbox.
4. **Rendering**: The frontend dispatches to the appropriate renderer (D3Chart, D3Graph, MermaidDiagram, P5Custom).
5. **Self-Healing**: If client-side validation fails, the error is sent back to the backend for automatic regeneration with error context.

---

## Deployment Guide

### Frontend Deployment on Vercel
Vite React apps can be deployed effortlessly on [Vercel](https://vercel.com/):

1. **Sign in to Vercel** and select **Add New Project**.
2. **Import your Git Repository**.
3. **Project Settings**:
   - **Root Directory**: Set this to `frontend`.
   - **Framework Preset**: Choose `Vite`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. **Environment Variables**:
   - Add `VITE_API_URL` pointing to your hosted FastAPI backend (e.g. `https://your-backend-api.onrender.com/api/v1`).
5. Click **Deploy**.

### Backend Deployment
You can deploy the FastAPI backend on hosting providers such as [Render](https://render.com/), [Railway](https://railway.app/), or [Heroku](https://www.heroku.com/):

1. Set the build environment to Python 3.11+.
2. Specify the **Start Command** from the `backend/` directory:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
3. Set all environment variables defined in the root `.env` (including `MONGODB_URL`, `PINECONE_API_KEY`, `LLM_PROVIDER`, etc.) inside the hosting provider's dashboard.

---

## Performance & Latency Benchmarks

The query and retrieval pipeline has been benchmarked using the local `all-MiniLM-L6-v2` embedding model and Pinecone serverless indexes.

### Benchmark Setup
- **Embedding Model**: `SentenceTransformer("all-MiniLM-L6-v2")` (384-dimensional dense vectors)
- **Vector Database**: Pinecone serverless index (`ytchatbot`)
- **Sample Query**: *"What is the main topic of the video?"*
- **Database Namespace**: Isolated by YouTube Video ID (tested with namespace containing 100 chunks)

### Latency Profiles
- **Local Embedding Latency**: ~`140.57 ms` (text-to-vector encoding on CPU)
- **Pinecone Search Latency (Cold/Warm-up Run)**: ~`350.61 ms`
- **Pinecone Search Latency (Warm/Average)**: ~`264.76 ms`
- **Total End-to-End Retrieval Overhead**: **~`350 ms - 400 ms`**

---

## License

This project is licensed under the [MIT License](LICENSE).