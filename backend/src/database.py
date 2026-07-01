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
    mongo_uri = StorageConfig.MONGODB_URL.strip().strip("\"'")
    client = AsyncIOMotorClient(mongo_uri, tlsCAFile=certifi.where())
    db = client[StorageConfig.DATABASE_NAME]
    
    await get_db().users.create_index("username", unique=True)
    await db.chat_sessions.create_index([("user_id", 1), ("created_at", -1)])
    await db.chat_messages.create_index([("session_id", 1), ("created_at", 1)])
    await db.playlist_videos.create_index([("playlist_id", 1), ("position", 1)])
    await db.playlist_videos.create_index([("playlist_id", 1), ("video_id", 1)], unique=True)
    await db.playlist_results.create_index("playlist_id", unique=True)
    await db.visualization_cache.create_index([("video_id", 1), ("created_at", -1)])
    await db.visualization_logs.create_index([("video_id", 1), ("created_at", -1)])
    
    return db


async def close_mongodb_connection():
    global client
    if client:
        client.close()


def get_db():
    if db is None:
        raise RuntimeError(
            "MongoDB not connected. Check that MONGODB_URL is set correctly "
            "in the .env file and that your MongoDB server is running."
        )
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
        return await get_db().users.find_one({"username": username})
    
    @staticmethod
    async def find_by_id(user_id: str) -> dict | None:
        return await get_db().users.find_one({"id": user_id})
    
    @staticmethod
    async def insert(user: dict) -> None:
        await get_db().users.insert_one(user)


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
        return await get_db().videos.find_one({"id": video_id})
    
    @staticmethod
    async def insert(video: dict) -> None:
        await get_db().videos.insert_one(video)


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
        cursor = get_db().chat_sessions.find({"user_id": user_id}).sort("created_at", -1)
        return await cursor.to_list(length=None)
    
    @staticmethod
    async def find_by_id(session_id: str) -> dict | None:
        return await get_db().chat_sessions.find_one({"id": session_id})
    
    @staticmethod
    async def insert(session: dict) -> str:
        await get_db().chat_sessions.insert_one(session)
        return session["id"]


class ChatMessage:
    @staticmethod
    async def create(session_id: str, role: str, content: str, visualization: dict | None = None) -> dict:
        doc = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc)
        }
        if visualization:
            doc["visualization"] = visualization
        return doc
    
    @staticmethod
    async def find_by_session(session_id: str) -> list:
        cursor = get_db().chat_messages.find({"session_id": session_id}).sort("created_at", 1)
        return await cursor.to_list(length=None)
    
    @staticmethod
    async def insert(message: dict) -> None:
        await get_db().chat_messages.insert_one(message)


class PlaylistVideo:
    """Metadata per video within a processed playlist."""

    @staticmethod
    async def create(playlist_id: str, video_id: str, title: str, position: int, summary: str, language: str) -> dict:
        doc = {
            "playlist_id": playlist_id,
            "video_id": video_id,
            "title": title,
            "position": position,
            "summary": summary,
            "language": language,
            "created_at": datetime.now(timezone.utc),
        }
        await get_db().playlist_videos.update_one(
            {"playlist_id": playlist_id, "video_id": video_id},
            {"$set": doc},
            upsert=True,
        )
        return doc

    @staticmethod
    async def find_by_playlist(playlist_id: str) -> list:
        cursor = get_db().playlist_videos.find({"playlist_id": playlist_id}).sort("position", 1)
        return await cursor.to_list(length=None)

    @staticmethod
    async def find_by_playlist_video(playlist_id: str, video_id: str) -> dict | None:
        return await get_db().playlist_videos.find_one({"playlist_id": playlist_id, "video_id": video_id})

    @staticmethod
    async def find_playlists_for_video(video_id: str) -> list:
        cursor = get_db().playlist_videos.find({"video_id": video_id})
        return await cursor.to_list(length=None)

    @staticmethod
    async def find_by_video_id(video_id: str) -> dict | None:
        return await get_db().playlist_videos.find_one({"video_id": video_id})


class PlaylistResult:
    """Processing result for a playlist — stores relation graph + video metadata."""

    @staticmethod
    async def create(playlist_id: str, relation_graph: dict, videos: list | None = None) -> dict:
        doc = {
            "playlist_id": playlist_id,
            "relation_graph": relation_graph,
            "videos": videos or [],
            "created_at": datetime.now(timezone.utc),
        }
        await get_db().playlist_results.insert_one(doc)
        return doc

    @staticmethod
    async def upsert(playlist_id: str, relation_graph: dict, videos: list | None = None) -> None:
        update = {"relation_graph": relation_graph, "created_at": datetime.now(timezone.utc)}
        if videos is not None:
            update["videos"] = videos
        await get_db().playlist_results.update_one(
            {"playlist_id": playlist_id},
            {"$set": update},
            upsert=True,
        )

    @staticmethod
    async def find_by_id(playlist_id: str) -> dict | None:
        return await get_db().playlist_results.find_one({"playlist_id": playlist_id})


class VisualizationCache:
    """Cached visualization specs to avoid LLM regeneration."""

    @staticmethod
    async def find_similar(video_id: str, query_emb: list[float], threshold: float = 0.90) -> dict | None:
        cursor = get_db().visualization_cache.find({"video_id": video_id})
        entries = await cursor.to_list(length=None)
        
        if not entries:
            return None
            
        best_match = None
        best_sim = -1.0
        
        norm1 = sum(a * a for a in query_emb) ** 0.5
        if norm1 == 0:
            return None
            
        for entry in entries:
            cached_emb = entry.get("query_embedding")
            if not cached_emb or len(cached_emb) != len(query_emb):
                continue
            
            dot = sum(a * b for a, b in zip(query_emb, cached_emb))
            norm2 = sum(b * b for b in cached_emb) ** 0.5
            if norm2 == 0:
                continue
            
            sim = dot / (norm1 * norm2)
            if sim > best_sim:
                best_sim = sim
                best_match = entry
                
        if best_sim >= threshold:
            print(f"[viz-cache] Hit! Similar query '{best_match['query']}' found with similarity {best_sim:.4f}")
            return best_match["spec"]
        return None

    @staticmethod
    async def insert(video_id: str, query: str, query_embedding: list[float], spec: dict) -> None:
        doc = {
            "video_id": video_id,
            "query": query,
            "query_embedding": query_embedding,
            "spec": spec,
            "created_at": datetime.now(timezone.utc)
        }
        await get_db().visualization_cache.insert_one(doc)


class VisualizationLog:
    """Logs of Tier 2 custom generations for review."""

    @staticmethod
    async def log(video_id: str, query: str, category: str, spec: dict | None, validation_error: str | None) -> None:
        doc = {
            "video_id": video_id,
            "query": query,
            "category": category,
            "spec": spec,
            "validation_error": validation_error,
            "created_at": datetime.now(timezone.utc)
        }
        await get_db().visualization_logs.insert_one(doc)