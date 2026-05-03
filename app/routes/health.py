import time
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database

router = APIRouter()

# Record when the app started
START_TIME = time.time()

@router.get("/health")
async def health_check(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Reports app uptime and MongoDB connection status.
    Tries a lightweight 'ping' command against the DB.
    """
    uptime_seconds = round(time.time() - START_TIME, 2)

    try:
        # 'ping' is the standard MongoDB health check command
        await db.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "uptime_seconds": uptime_seconds,
        "database": db_status,
    } 