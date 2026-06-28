# YTChatBot

AI-powered YouTube video and playlist chatbot that lets you ask questions about video content using RAG (Retrieval-Augmented Generation). It automatically extracts subtitles/transcripts, splits them into logical chunks, indexes them into a high-performance vector store, and provides context-aware answers to user queries with real-time streaming.

---

## Features

- **Video Processing**: Automatically extracts transcripts from YouTube videos using video IDs or URLs.
- **Playlist Support**: Process entire YouTube playlists sequentially, streaming the indexing status of each video in real-time.
- **Advanced RAG Chat**: Ask context-sensitive questions about video content using a multi-turn conversation memory.
- **Streaming Responses**: Real-time server-sent events (SSE) for AI answer generation.
- **MongoDB Integration**: Asynchronous database for storing user registrations, credentials (secured with bcrypt), chat sessions, message histories, and processed video logs.
- **Pinecone Vector Database**: High-speed, cloud-native vector similarity index for storing embeddings with namespace isolation per YouTube video ID.
- **JWT Authentication**: Secure user login and authorization logic.

---

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: MongoDB (via `motor` asynchronous driver)
- **Vector Database**: Pinecone
- **RAG Orchestration**: LangChain & LangChain-OpenAI
- **Embeddings**: SentenceTransformers (`all-MiniLM-L6-v2` - 384-dimensional dense vectors)
- **Authentication**: JWT (JSON Web Tokens) & Passlib (bcrypt)
- **Video Extraction**: yt-dlp & youtube-transcript-api

### Frontend
- **Framework**: React + Vite (JavaScript)
- **Styling**: TailwindCSS & Vanilla CSS
- **HTTP Client**: Axios (with token interceptors for auth)
- **Deployment**: Vercel-ready build output

---

## Project Structure

```
YTChatBot/
├── backend/                  # FastAPI Backend Service
│   ├── api/                  # API endpoints and validation models
│   │   ├── models.py         # Pydantic schemas for requests/responses
│   │   └── routes.py         # Routes (Auth, Video Processing, Playlists, Chats)
│   ├── src/                  # Core Business Logic
│   │   ├── auth.py           # Password hashing & JWT generation
│   │   ├── config.py         # Global configuration (loads environment variables)
│   │   ├── database.py       # MongoDB database client & operations
│   │   ├── rag_engine.py     # RAG pipeline with LangChain & Pinecone indexer
│   │   └── video_processor.py# YouTube transcript retrieval utilities
│   ├── data/                 # Local directory for cached assets
│   ├── main.py               # FastAPI server entry point
│   ├── requirements.txt      # Python backend packages
│   └── runtime.txt           # Python runtime version
├── frontend/                 # React Frontend Application
│   ├── src/                  # React source code (components, hooks, context)
│   │   ├── components/       # Reusable UI elements (chat panels, inputs)
│   │   ├── context/          # React contexts (e.g. Authentication status)
│   │   ├── hooks/            # Custom hooks
│   │   ├── services/         # API client handlers
│   │   └── main.jsx          # Entry point
│   ├── package.json          # Node dependencies and build scripts
│   └── vite.config.js        # Vite config
├── .env                      # Application environment variables (Git-ignored)
└── .env.example              # Sample environment template file
```

---

## Prerequisites

Before starting, ensure you have:
- **Python 3.11+**
- **Node.js 18+**
- A **MongoDB** database instance (local or [MongoDB Atlas Cloud](https://www.mongodb.com/cloud/atlas))
- A **Pinecone** account with an active API Key and Index ([Pinecone Console](https://console.pinecone.io/))
- An **OpenRouter API Key** ([OpenRouter](https://openrouter.ai/))
- A **Google API Key** (optional, for YouTube API metadata features)

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
# --- LLM Providers ---
# OpenRouter API Key for calling model endpoints
OPENROUTER_API_KEY=your_openrouter_api_key_here

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

# --- Third Party API Keys ---
# Google Developer Key for Youtube API (Optional)
GOOGLE_API_KEY=your_google_api_key_here
# NVIDIA Developer Key (Optional)
NVIDIA_API_KEY=your_nvidia_api_key_here
```

Configure these settings in `frontend/.env` file:
```env
VITE_API_URL=http://localhost:8000/api/v1
```

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
3. Set all environment variables defined in the root `.env` (including `MONGODB_URL`, `PINECONE_API_KEY`, etc.) inside the hosting provider's dashboard.

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