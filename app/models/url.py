from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class ShortenRequest(BaseModel):
    """What the client sends to POST /shorten"""
    original_url: HttpUrl
    custom_code: Optional[str] = None
    ttl_days: Optional[int] = 30


class ShortenResponse(BaseModel):
    """What we send back after shortening"""
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None


class URLDocument(BaseModel):
    """The shape of a document stored in MongoDB"""
    short_code: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    click_count: int = 0          # tracks total redirects, default 0