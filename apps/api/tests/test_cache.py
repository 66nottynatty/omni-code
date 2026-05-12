"""
Tests for the Redis caching layer.
"""

import pytest
from unittest.mock import MagicMock, patch
import json

from app.core.cache import RedisCache, get_cache, cache_key, cached


class TestRedisCache:
    """Test cases for RedisCache class."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = MagicMock()
        mock.ping.return_value = True
        return mock

    def test_cache_get_success(self, mock_redis):
        """Test successful cache get."""
        mock_redis.get.return_value = "test_value"

        cache = RedisCache()
        cache._client = mock_redis

        result = cache.get("test_key")
        assert result == "test_value"
        mock_redis.get.assert_called_once_with("test_key")

    def test_cache_get_miss(self, mock_redis):
        """Test cache get when key doesn't exist."""
        mock_redis.get.return_value = None

        cache = RedisCache()
        cache._client = mock_redis

        result = cache.get("nonexistent_key")
        assert result is None

    def test_cache_set(self, mock_redis):
        """Test cache set operation."""
        mock_redis.set.return_value = True

        cache = RedisCache()
        cache._client = mock_redis

        result = cache.set("test_key", "test_value")
        assert result is True
        mock_redis.set.assert_called_once_with("test_key", "test_value")

    def test_cache_set_with_ttl(self, mock_redis):
        """Test cache set with TTL."""
        mock_redis.setex.return_value = True

        cache = RedisCache()
        cache._client = mock_redis

        result = cache.set("test_key", "test_value", ttl=300)
        assert result is True
        mock_redis.setex.assert_called_once_with("test_key", 300, "test_value")

    def test_cache_delete(self, mock_redis):
        """Test cache delete operation."""
        mock_redis.delete.return_value = 1

        cache = RedisCache()
        cache._client = mock_redis

        result = cache.delete("test_key")
        assert result is True

    def test_cache_exists(self, mock_redis):
        """Test cache exists check."""
        mock_redis.exists.return_value = 1

        cache = RedisCache()
        cache._client = mock_redis

        result = cache.exists("test_key")
        assert result is True

    def test_cache_get_json(self, mock_redis):
        """Test getting and deserializing JSON from cache."""
        mock_redis.get.return_value = '{"key": "value", "number": 42}'

        cache = RedisCache()
        cache._client = mock_redis

        result = cache.get_json("test_key")
        assert result == {"key": "value", "number": 42}

    def test_cache_set_json(self, mock_redis):
        """Test serializing and storing JSON in cache."""
        mock_redis.set.return_value = True

        cache = RedisCache()
        cache._client = mock_redis

        result = cache.set_json("test_key", {"key": "value"})
        assert result is True
        mock_redis.set.assert_called()

    def test_cache_increment(self, mock_redis):
        """Test incrementing a counter."""
        mock_redis.incrby.return_value = 5

        cache = RedisCache()
        cache._client = mock_redis

        result = cache.increment("counter", 1)
        assert result == 5

    def test_cache_health_check_healthy(self, mock_redis):
        """Test health check when Redis is available."""
        mock_redis.ping.return_value = True

        cache = RedisCache()
        cache._client = mock_redis

        result = cache.health_check()
        assert result["status"] == "healthy"
        assert "latency_ms" in result

    def test_cache_handles_redis_errors_gracefully(self, mock_redis):
        """Test that cache operations handle errors gracefully."""
        import redis
        mock_redis.get.side_effect = redis.RedisError("Connection failed")

        cache = RedisCache()
        cache._client = mock_redis

        result = cache.get("test_key")
        assert result is None


class TestCacheKey:
    """Test cases for cache key generation."""

    def test_simple_key(self):
        """Test simple key generation."""
        key = cache_key("prefix", "arg1")
        assert key == "omnicode:prefix:arg1"

    def test_key_with_kwargs(self):
        """Test key generation with keyword arguments."""
        key = cache_key("prefix", "arg1", foo="bar", baz=123)
        assert "prefix" in key
        assert "arg1" in key
        assert "foo=bar" in key
        assert "baz=123" in key

    def test_key_with_long_args_uses_hash(self):
        """Test that very long keys use hash."""
        long_string = "a" * 300
        key = cache_key("prefix", long_string)
        assert "hash:" in key


class TestCachedDecorator:
    """Test cases for the cached decorator."""

    def test_sync_function_caching(self):
        """Test caching a synchronous function."""
        call_count = 0

        @cached("test", ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        mock_cache = MagicMock()
        mock_cache.get_json.return_value = None

        with patch("app.core.cache.get_cache", return_value=mock_cache):
            result = expensive_function(5)
            assert result == 10
            assert call_count == 1

            # Second call should use cached value
            mock_cache.get_json.return_value = 10
            result = expensive_function(5)
            assert result == 10
            assert call_count == 1  # Not incremented

    def test_cached_decorator_preserves_function_name(self):
        """Test that decorator preserves function metadata."""
        @cached("test")
        def my_function():
            return 42

        assert my_function.__name__ == "my_function"

    def test_cached_skips_with_skip_cache_flag(self):
        """Test that skip_cache flag bypasses cache."""
        call_count = 0

        @cached("test", skip_cache=True)
        def my_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        mock_cache = MagicMock()

        with patch("app.core.cache.get_cache", return_value=mock_cache):
            result = my_function(5)
            assert result == 10
            assert call_count == 1

            result = my_function(5)
            assert result == 10
            assert call_count == 2  # Called again, not cached

            # Cache should not have been checked or set
            mock_cache.get_json.assert_not_called()
            mock_cache.set_json.assert_not_called()


class TestCacheIntegration:
    """Integration tests for caching."""

    def test_get_cache_singleton(self):
        """Test that get_cache returns a singleton."""
        with patch("app.core.cache.settings") as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379"

            cache1 = get_cache()
            cache2 = get_cache()

            assert cache1 is cache2