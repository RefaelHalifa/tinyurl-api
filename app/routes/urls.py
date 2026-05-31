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


@router.post(
    "/shorten",
    response_model=ShortenResponse,
    summary="Shorten a URL",
    description=(
        "Creates a shortened URL for the given original URL.\n\n"
        "- Optionally provide a **custom alias** (3–20 alphanumeric chars, hyphens, underscores)\n"
        "- Optionally set a **TTL in days** (default: 30). The short URL expires after this period.\n"
        "- Returns the generated short code and the full short URL."
    ),
    responses={
        409: {"description": "Custom alias is already taken"},
        422: {"description": "Validation error — invalid URL or custom code format"},
    },
)
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


@router.get(
    "/stats/{code}",
    response_model=StatsResponse,
    summary="Get URL stats",
    description=(
        "Returns metadata and total click count for a short code.\n\n"
        "- `click_count` is read from Cassandra (the analytics store)\n"
        "- Does **not** trigger a redirect or increment the counter"
    ),
    responses={
        404: {"description": "Short code not found"},
    },
)
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


@router.get(
    "/analytics/{code}",
    response_model=AnalyticsResponse,
    summary="Get click history",
    description=(
        "Returns the full click history for a short code, with individual timestamps.\n\n"
        "- Each entry represents one redirect event\n"
        "- Timestamps are stored in Cassandra using `TIMEUUID` for time-ordered retrieval\n"
        "- Does **not** trigger a redirect or increment the counter"
    ),
    responses={
        404: {"description": "Short code not found"},
    },
)
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


@router.get(
    "/{code}",
    summary="Redirect to original URL",
    description=(
        "Redirects the client to the original URL associated with the given short code.\n\n"
        "- Checks Redis cache first; falls back to MongoDB on cache miss\n"
        "- Publishes a click event to Kafka for async analytics processing\n"
        "- Returns `307 Temporary Redirect`\n"
        "- Returns `410 Gone` if the short URL has expired"
    ),
    responses={
        307: {"description": "Redirect to the original URL"},
        404: {"description": "Short code not found"},
        410: {"description": "Short URL has expired"},
    },
)
async def redirect_url(code: str):
    cached_url = await get_cached_url(code)
    if cached_url:
        await publish_click_event(code)
        return RedirectResponse(url=cached_url, status_code=307)

    document = await database.db["urls"].find_one({"short_code": code})
    if not document:
        raise HTTPException(status_code=404, detail="Short URL not found")

    if document.get("expires_at"):
        expires_at = document["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="This short URL has expired")

    await set_cached_url(code, document["original_url"])
    await publish_click_event(code)
    return RedirectResponse(url=document["original_url"], status_code=307)