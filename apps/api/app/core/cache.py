"""
Redis-based caching layer for API responses.
"""

from functools import wraps
from typing import Optional, Callable, Any, Union
import json
import hashlib
import structlog
from datetime import datetime, timedelta

import redis
from app.core.config import get_settings

logger = structlog.get_logger()

settings = get_settings()


class RedisCache:
    """Redis-backed cache with simple operations."""

    def __init__(self, redis_url: Optional[str] = None):
        self._redis_url = redis_url or settings.redis_url
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> Union[redis.Redis, Any]:
        if self._client is None:
            if settings.redis_cluster:
                from redis.cluster import RedisCluster
                self._client = RedisCluster.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
            else:
                self._client = redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
        return self._client

    def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        try:
            return self.client.get(key)
        except redis.RedisError as e:
            logger.warning("cache_get_error", key=key, error=str(e))
            return None

    def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set a value in cache with optional TTL in seconds."""
        try:
            if ttl:
                return self.client.setex(key, ttl, value)
            return self.client.set(key, value)
        except redis.RedisError as e:
            logger.warning("cache_set_error", key=key, error=str(e))
            return False

    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            return bool(self.client.delete(key))
        except redis.RedisError as e:
            logger.warning("cache_delete_error", key=key, error=str(e))
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(self.client.exists(key))
        except redis.RedisError as e:
            logger.warning("cache_exists_error", key=key, error=str(e))
            return False

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in cache."""
        try:
            return self.client.incrby(key, amount)
        except redis.RedisError as e:
            logger.warning("cache_increment_error", key=key, error=str(e))
            return None

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time on a key."""
        try:
            return self.client.expire(key, ttl)
        except redis.RedisError as e:
            logger.warning("cache_expire_error", key=key, error=str(e))
            return False

    def get_json(self, key: str) -> Optional[Any]:
        """Get and deserialize JSON value."""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Serialize and store JSON value."""
        try:
            serialized = json.dumps(value, default=str)
            return self.set(key, serialized, ttl)
        except (TypeError, ValueError) as e:
            logger.error("cache_json_serialize_error", key=key, error=str(e))
            return False

    def ping(self) -> bool:
        """Check if Redis is available."""
        try:
            return self.client.ping()
        except redis.RedisError:
            return False

    def health_check(self) -> dict:
        """Return health status of Redis connection."""
        try:
            start = datetime.utcnow()
            self.client.ping()
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            return {"status": "healthy", "latency_ms": round(latency, 2)}
        except redis.RedisError as e:
            return {"status": "unhealthy", "error": str(e)}


_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_str = ":".join(key_parts)
    if len(key_str) > 200:
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:32]
        return f"omnicode:hash:{key_hash}"
    return f"omnicode:{key_str}"


def cached(
    key_prefix: str,
    ttl: int = 300,
    skip_cache: bool = False,
) -> Callable:
    """
    Decorator to cache function results in Redis.

    Args:
        key_prefix: Prefix for the cache key
        ttl: Time to live in seconds (default 5 minutes)
        skip_cache: Skip caching (useful in testing)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if skip_cache:
                return await func(*args, **kwargs)

            cache = get_cache()
            key = cache_key(key_prefix, *args, **kwargs)

            cached_value = cache.get_json(key)
            if cached_value is not None:
                logger.debug("cache_hit", key=key, function=func.__name__)
                return cached_value

            logger.debug("cache_miss", key=key, function=func.__name__)
            result = await func(*args, **kwargs)

            if result is not None:
                cache.set_json(key, result, ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if skip_cache:
                return func(*args, **kwargs)

            cache = get_cache()
            key = cache_key(key_prefix, *args, **kwargs)

            cached_value = cache.get_json(key)
            if cached_value is not None:
                logger.debug("cache_hit", key=key, function=func.__name__)
                return cached_value

            logger.debug("cache_miss", key=key, function=func.__name__)
            result = func(*args, **kwargs)

            if result is not None:
                cache.set_json(key, result, ttl)

            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


import asyncio