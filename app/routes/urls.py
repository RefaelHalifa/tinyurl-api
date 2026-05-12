from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone, timedelta

from app.models.url import ShortenRequest, ShortenResponse, StatsResponse
from app.services.shortener import generate_short_code
from app.services.cache_service import get_cached_url, set_cached_url
from app.services.kafka_producer import publish_click_event
import app.database as database

router = APIRouter()

BASE_URL = "http://localhost:8000"
MAX_RETRIES = 5  # max collision retries before giving up


@router.post("/shorten", response_model=ShortenResponse)
async def shorten_url(request: ShortenRequest):
    original_url = str(request.url)

    # --- Resolve the short code ---
    if request.custom_code:
        # User wants a specific alias — check if it's already taken
        existing = await database.db["urls"].find_one({"short_code": request.custom_code})
        if existing:
            raise HTTPException(status_code=409, detail="Custom alias already taken")
        short_code = request.custom_code
    else:
        # Auto-generate a unique Base62 code
        for _ in range(MAX_RETRIES):
            short_code = generate_short_code()
            existing = await database.db["urls"].find_one({"short_code": short_code})
            if not existing:
                break
        else:
            raise HTTPException(status_code=500, detail="Could not generate unique short code")

    # --- Compute expiry ---
    ttl_days = request.ttl_days if request.ttl_days is not None else 30
    expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)

    document = {
        "short_code": short_code,
        "original_url": original_url,
        "created_at": datetime.now(timezone.utc),
        "click_count": 0,
        "expires_at": expires_at,
    }

    await database.db["urls"].insert_one(document)

    return ShortenResponse(
        short_code=short_code,
        short_url=f"{BASE_URL}/{short_code}",
        original_url=original_url,
        created_at=document["created_at"],
        expires_at=expires_at,
    )


@router.get("/stats/{code}", response_model=StatsResponse)
async def get_stats(code: str):
    document = await database.db["urls"].find_one({"short_code": code})
    if not document:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return StatsResponse(
        short_code=document["short_code"],
        original_url=document["original_url"],
        click_count=document.get("click_count", 0),
        created_at=document["created_at"],
        expires_at=document.get("expires_at"),
    )


@router.get("/{code}")
async def redirect_url(code: str):
    cached_url = await get_cached_url(code)
    if cached_url:
        # Increment click counter even on cache hit
        await database.db["urls"].update_one(
            {"short_code": code},
            {"$inc": {"click_count": 1}}
        )
        await publish_click_event(code)  # fire click event to Kafka
        return RedirectResponse(url=cached_url, status_code=307)

    document = await database.db["urls"].find_one({"short_code": code})
    if not document:
        raise HTTPException(status_code=404, detail="Short URL not found")

    await set_cached_url(code, document["original_url"])

    # Increment click counter
    await database.db["urls"].update_one(
        {"short_code": code},
        {"$inc": {"click_count": 1}}
    )
    await publish_click_event(code)  # fire click event to Kafka
    return RedirectResponse(url=document["original_url"], status_code=307)