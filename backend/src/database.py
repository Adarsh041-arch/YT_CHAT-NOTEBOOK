"""Database configuration and models."""

import os
from datetime import datetime, timezone
import uuid
import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from .config import StorageConfig

client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None


async def connect_to_mongodb():
    global client, db
    client = AsyncIOMotorClient(StorageConfig.MONGODB_URL,tls=True,tlsCAFile=certifi.where())
    db = client[StorageConfig.DATABASE_NAME]
    
    await db.users.create_index("username", unique=True)
    await db.chat_sessions.create_index([("user_id", 1), ("created_at", -1)])
    await db.chat_messages.create_index([("session_id", 1), ("created_at", 1)])
    
    return db


async def close_mongodb_connection():
    global client
    if client:
        client.close()


def get_db():
    return db


class User:
    @staticmethod
    async def create(username: str, password_hash: str) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "username": username,
            "password_hash": password_hash,
            "created_at": datetime.now(timezone.utc)
        }
    
    @staticmethod
    async def find_by_username(username: str) -> dict | None:
        return await db.users.find_one({"username": username})
    
    @staticmethod
    async def find_by_id(user_id: str) -> dict | None:
        return await db.users.find_one({"id": user_id})
    
    @staticmethod
    async def insert(user: dict) -> None:
        await db.users.insert_one(user)


class Video:
    @staticmethod
    async def create(video_id: str, language: str, chunks_created: int) -> dict:
        return {
            "id": video_id,
            "language": language,
            "chunks_created": chunks_created,
            "created_at": datetime.now(timezone.utc)
        }
    
    @staticmethod
    async def find_by_id(video_id: str) -> dict | None:
        return await db.videos.find_one({"id": video_id})
    
    @staticmethod
    async def insert(video: dict) -> None:
        await db.videos.insert_one(video)


class ChatSession:
    @staticmethod
    async def create(user_id: str, video_id: str, title: str = "New Chat") -> dict:
        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "video_id": video_id,
            "title": title,
            "created_at": datetime.now(timezone.utc)
        }
    
    @staticmethod
    async def find_by_user(user_id: str) -> list:
        cursor = db.chat_sessions.find({"user_id": user_id}).sort("created_at", -1)
        return await cursor.to_list(length=None)
    
    @staticmethod
    async def find_by_id(session_id: str) -> dict | None:
        return await db.chat_sessions.find_one({"id": session_id})
    
    @staticmethod
    async def insert(session: dict) -> str:
        await db.chat_sessions.insert_one(session)
        return session["id"]


class ChatMessage:
    @staticmethod
    async def create(session_id: str, role: str, content: str) -> dict:
        return {
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc)
        }
    
    @staticmethod
    async def find_by_session(session_id: str) -> list:
        cursor = db.chat_messages.find({"session_id": session_id}).sort("created_at", 1)
        return await cursor.to_list(length=None)
    
    @staticmethod
    async def insert(message: dict) -> None:
        await db.chat_messages.insert_one(message)