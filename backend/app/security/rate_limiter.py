"""Rate limiter middleware — Redis-based, keyed by API key or IP."""

from fastapi import HTTPException, Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


class RateLimiter:
    """Simple sliding-window rate limiter backed by Redis."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def check(self, request: Request, key: str) -> None:
        """Raise 429 if the key has exceeded the rate limit."""
        redis = request.app.state.redis
        redis_key = f"ratelimit:{key}"

        import time

        now = time.time()
        pipe = redis.pipeline()
        # Remove entries outside the window
        pipe.zremrangebyscore(redis_key, 0, now - self.window_seconds)
        # Count entries in the window
        pipe.zcard(redis_key)
        # Add the current request
        pipe.zadd(redis_key, {str(now): now})
        # Set TTL so keys auto-expire
        pipe.expire(redis_key, self.window_seconds)
        results = await pipe.execute()

        current_count = results[1]
        if current_count >= self.max_requests:
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
            )


# Default instance — 100 requests per 60 seconds per key
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
