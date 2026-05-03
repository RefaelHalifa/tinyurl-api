from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

# Module-level variables — set during app startup
mongo_client: AsyncIOMotorClient = None
db = None

def get_database():
    """Returns the active database instance."""
    return db

async def connect_db():
    """Called at app startup — creates the Motor client."""
    global mongo_client, db
    mongo_client = AsyncIOMotorClient(settings.mongo_url)
    db = mongo_client[settings.mongo_db_name]

async def close_db():
    """Called at app shutdown — closes the Motor connection."""
    global mongo_client
    if mongo_client:
        mongo_client.close()