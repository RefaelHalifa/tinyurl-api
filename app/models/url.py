from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional


class ShortenRequest(BaseModel):
    """What the client sends to POST /shorten"""
    original_url: HttpUrl                  # Pydantic validates this is a real URL
    custom_code: Optional[str] = None      # Optional custom alias (e.g. "my-sale")
    ttl_days: Optional[int] = 30           # How many days until the link expires


class ShortenResponse(BaseModel):
    """What we send back after shortening"""
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: datetime                   # TU-5: when this link will be deleted


class URLDocument(BaseModel):
    """The shape of a document stored in MongoDB"""
    short_code: str
    original_url: str
    created_at: datetime
    click_count: int = 0                   # TU-6 will use this
    expires_at: Optional[datetime] = None  # TU-5: TTL field for MongoDB index