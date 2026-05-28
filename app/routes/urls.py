from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone, timedelta

from app.models.url import ShortenRequest, ShortenResponse, StatsResponse, AnalyticsResponse, ClickEvent
from app.services.shortener import generate_short_code
from app.services.cache_service import get_cached_url, set_cached_url
from app.services.kafka_producer import publish_click_event
from app.services.cassandra_service import cassandra_service
import app.database as database

router = APIRouter()

BASE_URL = "http://localhost:8000"
MAX_RETRIES = 5  # max collision retries before giving up


@router.post("/shorten", response_model=ShortenResponse)
async def shorten_url(request: ShortenRequest):
    original_url = str(request.original_url)

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

    click_count = cassandra_service.get_click_count(code)

    return StatsResponse(
        short_code=document["short_code"],
        original_url=document["original_url"],
        click_count=click_count,
        created_at=document["created_at"],
        expires_at=document.get("expires_at"),
    )


@router.get("/analytics/{code}", response_model=AnalyticsResponse)
async def get_analytics(code: str):
    document = await database.db["urls"].find_one({"short_code": code})
    if not document:
        raise HTTPException(status_code=404, detail="Short URL not found")

    clicks = cassandra_service.get_clicks(code)

    return AnalyticsResponse(
        short_code=code,
        total_clicks=len(clicks),
        clicks=[ClickEvent(clicked_at=c["clicked_at"]) for c in clicks],
    )


@router.get("/{code}")
async def redirect_url(code: str):
    cached_url = await get_cached_url(code)
    if cached_url:
        await publish_click_event(code)
        return RedirectResponse(url=cached_url, status_code=307)

    document = await database.db["urls"].find_one({"short_code": code})
    if not document:
        raise HTTPException(status_code=404, detail="Short URL not found")

    if document.get("expires_at") and document["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="This short URL has expired")

    await set_cached_url(code, document["original_url"])
    await publish_click_event(code)
    return RedirectResponse(url=document["original_url"], status_code=307)