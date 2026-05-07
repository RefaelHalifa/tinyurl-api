import app.database as db

CACHE_TTL = 3600  # 1 hour — resets on every cache hit


async def get_cached_url(short_code: str) -> str | None:
    """Try to get URL from Redis. Refreshes TTL on every hit (sliding expiration)."""
    key = f"url:{short_code}"
    value = await db.redis.get(key)
    if value:
        await db.redis.expire(key, CACHE_TTL)  # popular URLs stay cached
        return value.decode("utf-8")
    return None


async def set_cached_url(short_code: str, original_url: str) -> None:
    """Store URL in Redis with TTL."""
    await db.redis.set(f"url:{short_code}", original_url, ex=CACHE_TTL)


async def delete_cached_url(short_code: str) -> None:
    """Remove URL from cache (used on deletion or expiry)."""
    await db.redis.delete(f"url:{short_code}")