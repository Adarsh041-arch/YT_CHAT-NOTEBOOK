"""Database configuration and models."""

from sqlalchemy import create_engine, Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone
import uuid
from .config import StorageConfig

StorageConfig.ensure_dirs()

engine = create_engine(
    f"sqlite:///{StorageConfig.DB_PATH}",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

class Video(Base):
    __tablename__ = "videos"
    id = Column(String, primary_key=True, index=True) # YouTube video ID
    language = Column(String)
    chunks_created = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"))
    video_id = Column(String, ForeignKey("videos.id"))
    title = Column(String, default="New Chat") # Optional title
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="sessions")
    video = relationship("Video")
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.created_at", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    role = Column(String) # "user" or "assistant"
    content = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session = relationship("ChatSession", back_populates="messages")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
