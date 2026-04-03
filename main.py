"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import APIConfig
from api.routes import router, video_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("Starting YTChatBot API...")
    yield
    print("Shutting down YTChatBot API...")
    video_store.clear()


app = FastAPI(
    title=APIConfig.TITLE,
    version=APIConfig.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "YTChatBot API",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=APIConfig.HOST,
        port=APIConfig.PORT,
        reload=True,
    )
