"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import APIConfig
from src.database import connect_to_mongodb, close_mongodb_connection
from api.routes import router, engine_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("Starting YTChatBot API...")
    try:
        await connect_to_mongodb()
        print("MongoDB connected")
    except Exception as e:
        print("MongoDB startup failed:", e)
    yield
    print("Shutting down YTChatBot API...")
    await close_mongodb_connection()
    engine_store.clear()


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
