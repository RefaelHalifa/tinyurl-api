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

    model_config = {
        "json_schema_extra": {
            "example": {
                "original_url": "https://www.example.com/some/very/long/path",
                "custom_code": "my-link",
                "ttl_days": 30,
            }
        }
    }


class ShortenResponse(BaseModel):
    """What we send back after shortening"""
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "short_code": "my-link",
                "short_url": "http://localhost:8000/my-link",
                "original_url": "https://www.example.com/some/very/long/path",
                "created_at": "2026-05-31T10:00:00Z",
                "expires_at": "2026-06-30T10:00:00Z",
            }
        }
    }


class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "short_code": "my-link",
                "original_url": "https://www.example.com/some/very/long/path",
                "click_count": 42,
                "created_at": "2026-05-31T10:00:00Z",
                "expires_at": "2026-06-30T10:00:00Z",
            }
        }
    }


class URLDocument(BaseModel):
    """The shape of a document stored in MongoDB"""
    short_code: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class ClickEvent(BaseModel):
    clicked_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "clicked_at": "2026-05-31T11:23:45Z"
            }
        }
    }


class AnalyticsResponse(BaseModel):
    short_code: str
    total_clicks: int
    clicks: list[ClickEvent]

    model_config = {
        "json_schema_extra": {
            "example": {
                "short_code": "my-link",
                "total_clicks": 3,
                "clicks": [
                    {"clicked_at": "2026-05-31T11:00:00Z"},
                    {"clicked_at": "2026-05-31T11:15:00Z"},
                    {"clicked_at": "2026-05-31T11:23:45Z"},
                ],
            }
        }
    }