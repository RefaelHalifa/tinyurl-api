from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone

from app.models.url import ShortenRequest, ShortenResponse
from app.services.shortener import generate_short_code
import app.database as database

router = APIRouter()

BASE_URL = "http://localhost:8000"
MAX_RETRIES = 5  # max collision retries before giving up


@router.post("/shorten", response_model=ShortenResponse)
async def shorten_url(request: ShortenRequest):
    original_url = str(request.original_url)  # convert HttpUrl → plain string

    # Try to generate a unique short code (retry on collision)
    for _ in range(MAX_RETRIES):
        short_code = generate_short_code()

        # Check if this code already exists in MongoDB
        existing = await database.db["urls"].find_one({"short_code": short_code})
        if not existing:
            break  # unique code found — exit the loop
    else:
        # All retries failed (extremely rare)
        raise HTTPException(status_code=500, detail="Could not generate unique short code")

    # Build the document to store in MongoDB
    document = {
        "short_code": short_code,
        "original_url": original_url,
        "created_at": datetime.now(timezone.utc),
        "click_count": 0,
    }

    # Insert into MongoDB
    await database.db["urls"].insert_one(document)

    return ShortenResponse(
        short_code=short_code,
        short_url=f"{BASE_URL}/{short_code}",
        original_url=original_url,
        created_at=document["created_at"],
    )