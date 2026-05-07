from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone

from app.models.url import ShortenRequest, ShortenResponse
from app.services.shortener import generate_short_code
from app.services.cache_service import get_cached_url, set_cached_url
import app.database as database

router = APIRouter()

BASE_URL = "http://localhost:8000"
MAX_RETRIES = 5  # max collision retries before giving up


@router.post("/shorten", response_model=ShortenResponse)
async def shorten_url(request: ShortenRequest):
    original_url = str(request.original_url)  # convert HttpUrl → plain string

    for _ in range(MAX_RETRIES):
        short_code = generate_short_code()
        existing = await database.db["urls"].find_one({"short_code": short_code})
        if not existing:
            break  # unique code found — exit the loop
    else:
        raise HTTPException(status_code=500, detail="Could not generate unique short code")

    document = {
        "short_code": short_code,
        "original_url": original_url,
        "created_at": datetime.now(timezone.utc),
        "click_count": 0,
    }

    await database.db["urls"].insert_one(document)
    
    return ShortenResponse(
        short_code=short_code,
        short_url=f"{BASE_URL}/{short_code}",
        original_url=original_url,
        created_at=document["created_at"],
    )


@router.get("/{code}")
async def redirect_url(code: str):
    cached_url = await get_cached_url(code)  # check cache first
    if cached_url:
        return RedirectResponse(url=cached_url, status_code=307)

    document = await database.db["urls"].find_one({"short_code": code})
    if not document:
        raise HTTPException(status_code=404, detail="Short URL not found")

    await set_cached_url(code, document["original_url"])  # populate cache on miss
    return RedirectResponse(url=document["original_url"], status_code=307)