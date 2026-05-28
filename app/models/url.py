from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional
from datetime import datetime
import re


class ShortenRequest(BaseModel):
    """What the client sends to POST /shorten"""
    original_url: HttpUrl
    custom_code: Optional[str] = None
    ttl_days: Optional[int] = 30

    @field_validator("custom_code")
    @classmethod
    def validate_custom_code(cls, v):
        if v is None:
            return v
        if len(v) < 3 or len(v) > 20:
            raise ValueError("Custom code must be between 3 and 20 characters")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Custom code may only contain letters, numbers, hyphens, and underscores")
        return v


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


class ClickEvent(BaseModel):
    clicked_at: datetime


class AnalyticsResponse(BaseModel):
    short_code: str
    total_clicks: int
    clicks: list[ClickEvent]