"""
Redis cache implementation for distributed caching
"""

import json
import logging
from typing import Optional, Any, Dict
import hashlib

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Install with: pip install redis")


class RedisCache:
    """
    Redis-based cache for distributed systems
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ttl_seconds: int = 300,
        prefix: str = "comfyui:cache:",
    ):
        """
        Initialize Redis cache

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            ttl_seconds: Default TTL for cache entries
            prefix: Key prefix for namespacing
        """
        if not REDIS_AVAILABLE:
            raise ImportError("Redis library not installed")

        self.ttl_seconds = ttl_seconds
        self.prefix = prefix

        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

        # Test connection
        try:
            self.client.ping()
            logger.info(f"Connected to Redis at {host}:{port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _generate_key(self, request_path: str, params: Dict[str, Any]) -> str:
        """Generate cache key"""
        key_str = f"{request_path}:{sorted(params.items())}"
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{self.prefix}{key_hash}"

    def get(self, request_path: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached value"""
        key = self._generate_key(request_path, params)

        try:
            value = self.client.get(key)
            if value:
                logger.debug(f"Redis cache hit for {key}")
                return json.loads(value)
            else:
                logger.debug(f"Redis cache miss for {key}")
                return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(
        self,
        request_path: str,
        params: Dict[str, Any],
        value: Any,
        ttl: Optional[int] = None,
    ):
        """Set cache value"""
        key = self._generate_key(request_path, params)
        ttl = ttl or self.ttl_seconds

        try:
            serialized = json.dumps(value)
            self.client.setex(key, ttl, serialized)
            logger.debug(f"Redis cache set for {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def delete(self, request_path: str, params: Dict[str, Any]):
        """Delete cached value"""
        key = self._generate_key(request_path, params)

        try:
            self.client.delete(key)
            logger.debug(f"Redis cache deleted for {key}")
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    def clear(self):
        """Clear all cache with prefix"""
        try:
            keys = self.client.keys(f"{self.prefix}*")
            if keys:
                self.client.delete(*keys)
                logger.info(f"Cleared {len(keys)} Redis cache entries")
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            info = self.client.info("stats")
            keys_count = len(self.client.keys(f"{self.prefix}*"))

            return {
                "keys_count": keys_count,
                "total_connections": info.get("total_connections_received", 0),
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / max(
                        info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0),
                        1,
                    )
                ),
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {}

    def health_check(self) -> bool:
        """Check if Redis is healthy"""
        try:
            self.client.ping()
            return True
        except Exception:
            return False


class RateLimiterRedis:
    """
    Redis-based rate limiter for distributed systems
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        prefix: str = "comfyui:ratelimit:",
    ):
        """
        Initialize Redis rate limiter

        Args:
            redis_client: Redis client instance
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            prefix: Key prefix
        """
        self.client = redis_client
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.prefix = prefix

    def is_allowed(self, identifier: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed using Redis

        Uses sliding window with sorted sets
        """
        import time

        now = time.time()

        minute_key = f"{self.prefix}{identifier}:minute"
        hour_key = f"{self.prefix}{identifier}:hour"

        try:
            # Use pipeline for atomic operations
            pipe = self.client.pipeline()

            # Minute window
            minute_ago = now - 60
            pipe.zremrangebyscore(minute_key, 0, minute_ago)
            pipe.zadd(minute_key, {str(now): now})
            pipe.zcard(minute_key)
            pipe.expire(minute_key, 60)

            # Hour window
            hour_ago = now - 3600
            pipe.zremrangebyscore(hour_key, 0, hour_ago)
            pipe.zadd(hour_key, {str(now): now})
            pipe.zcard(hour_key)
            pipe.expire(hour_key, 3600)

            results = pipe.execute()

            minute_count = results[2]
            hour_count = results[6]

            # Check limits
            if minute_count > self.requests_per_minute:
                return False, {
                    "reason": "rate_limit_minute",
                    "limit": self.requests_per_minute,
                    "window": "minute",
                    "retry_after": 60,
                }

            if hour_count > self.requests_per_hour:
                return False, {
                    "reason": "rate_limit_hour",
                    "limit": self.requests_per_hour,
                    "window": "hour",
                    "retry_after": 3600,
                }

            return True, {
                "requests_remaining_minute": self.requests_per_minute - minute_count,
                "requests_remaining_hour": self.requests_per_hour - hour_count,
            }

        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fail open - allow request on Redis error
            return True, {"error": str(e)}


def create_redis_cache(redis_url: str, **kwargs) -> RedisCache:
    """
    Factory function to create Redis cache from URL

    Args:
        redis_url: Redis URL (e.g., redis://localhost:6379/0)
        **kwargs: Additional arguments for RedisCache

    Returns:
        RedisCache instance
    """
    # Parse Redis URL
    from urllib.parse import urlparse

    parsed = urlparse(redis_url)

    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    db = int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0
    password = parsed.password

    return RedisCache(host=host, port=port, db=db, password=password, **kwargs)
