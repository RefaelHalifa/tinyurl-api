from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as aioredis
from app.config import settings

# Module-level variables — set during app startup
mongo_client: AsyncIOMotorClient = None
db = None
redis: aioredis.Redis = None


def get_database():
    """Returns the active MongoDB database instance."""
    return db


async def connect_db():
    """Called at app startup — creates Motor and Redis clients."""
    global mongo_client, db, redis

    # MongoDB
    mongo_client = AsyncIOMotorClient(settings.mongo_url)
    db = mongo_client[settings.mongo_db_name]

    # Redis
    redis = await aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=False,  # we decode manually in cache_service
    )


async def close_db():
    """Called at app shutdown — closes all connections."""
    global mongo_client, redis

    if mongo_client:
        mongo_client.close()

    if redis:
        await redis.aclose()