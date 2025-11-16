"""
Advanced middleware for enterprise features
Includes rate limiting, caching, and request logging
"""

import time
import hashlib
import logging
from typing import Optional, Dict, Any, Callable
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter

    Implements sliding window rate limiting per IP/API key
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
    ):
        """
        Initialize rate limiter

        Args:
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            burst_size: Max burst requests
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size

        # Storage: {identifier: {window: [timestamps]}}
        self.requests: Dict[str, Dict[str, list]] = defaultdict(lambda: {"minute": [], "hour": []})
        self.burst_tokens: Dict[str, int] = defaultdict(lambda: burst_size)
        self.last_refill: Dict[str, float] = {}

    def _cleanup_old_requests(self, identifier: str):
        """Remove old request timestamps"""
        now = time.time()

        # Cleanup minute window
        minute_ago = now - 60
        self.requests[identifier]["minute"] = [
            ts for ts in self.requests[identifier]["minute"] if ts > minute_ago
        ]

        # Cleanup hour window
        hour_ago = now - 3600
        self.requests[identifier]["hour"] = [
            ts for ts in self.requests[identifier]["hour"] if ts > hour_ago
        ]

    def _refill_burst_tokens(self, identifier: str):
        """Refill burst tokens (1 per second)"""
        now = time.time()
        last_refill = self.last_refill.get(identifier, now)
        time_passed = now - last_refill

        if time_passed >= 1.0:
            tokens_to_add = int(time_passed)
            self.burst_tokens[identifier] = min(
                self.burst_size, self.burst_tokens[identifier] + tokens_to_add
            )
            self.last_refill[identifier] = now

    def is_allowed(self, identifier: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed

        Args:
            identifier: Unique identifier (IP, API key, etc.)

        Returns:
            Tuple of (allowed, info_dict)
        """
        now = time.time()

        # Cleanup old requests
        self._cleanup_old_requests(identifier)

        # Refill burst tokens
        self._refill_burst_tokens(identifier)

        # Count current requests
        minute_count = len(self.requests[identifier]["minute"])
        hour_count = len(self.requests[identifier]["hour"])

        # Check limits
        if minute_count >= self.requests_per_minute:
            return False, {
                "reason": "rate_limit_minute",
                "limit": self.requests_per_minute,
                "window": "minute",
                "retry_after": 60,
            }

        if hour_count >= self.requests_per_hour:
            return False, {
                "reason": "rate_limit_hour",
                "limit": self.requests_per_hour,
                "window": "hour",
                "retry_after": 3600,
            }

        # Check burst limit
        if self.burst_tokens[identifier] <= 0:
            return False, {
                "reason": "rate_limit_burst",
                "limit": self.burst_size,
                "window": "burst",
                "retry_after": 1,
            }

        # Allow request
        self.requests[identifier]["minute"].append(now)
        self.requests[identifier]["hour"].append(now)
        self.burst_tokens[identifier] -= 1

        return True, {
            "requests_remaining_minute": self.requests_per_minute - minute_count - 1,
            "requests_remaining_hour": self.requests_per_hour - hour_count - 1,
            "burst_tokens_remaining": self.burst_tokens[identifier],
        }

    def get_stats(self, identifier: str) -> Dict[str, Any]:
        """Get current rate limit stats for identifier"""
        self._cleanup_old_requests(identifier)
        self._refill_burst_tokens(identifier)

        minute_count = len(self.requests[identifier]["minute"])
        hour_count = len(self.requests[identifier]["hour"])

        return {
            "requests_per_minute": minute_count,
            "requests_per_hour": hour_count,
            "limit_per_minute": self.requests_per_minute,
            "limit_per_hour": self.requests_per_hour,
            "burst_tokens": self.burst_tokens[identifier],
            "burst_limit": self.burst_size,
        }


class RequestCache:
    """
    Simple in-memory request cache
    Can be replaced with Redis for distributed systems
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache

        Args:
            ttl_seconds: Time to live for cache entries
        """
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, tuple[Any, float]] = {}

    def _generate_key(self, request_path: str, params: Dict[str, Any]) -> str:
        """Generate cache key from request"""
        key_str = f"{request_path}:{sorted(params.items())}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, request_path: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached response"""
        key = self._generate_key(request_path, params)

        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                logger.debug(f"Cache hit for {key}")
                return value
            else:
                # Expired, remove
                del self.cache[key]
                logger.debug(f"Cache expired for {key}")

        logger.debug(f"Cache miss for {key}")
        return None

    def set(self, request_path: str, params: Dict[str, Any], value: Any):
        """Set cache value"""
        key = self._generate_key(request_path, params)
        expiry = time.time() + self.ttl_seconds
        self.cache[key] = (value, expiry)
        logger.debug(f"Cache set for {key}")

    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        logger.info("Cache cleared")

    def cleanup_expired(self):
        """Remove expired entries"""
        now = time.time()
        expired_keys = [k for k, (_, expiry) in self.cache.items() if expiry < now]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


class RequestLogger:
    """
    Advanced request logging with metrics
    """

    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_duration = 0.0
        self.requests_by_endpoint: Dict[str, int] = defaultdict(int)
        self.errors_by_type: Dict[str, int] = defaultdict(int)

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        ip: str,
        user_agent: Optional[str] = None,
    ):
        """Log request with metrics"""
        self.request_count += 1
        self.total_duration += duration
        self.requests_by_endpoint[path] += 1

        if status_code >= 400:
            self.error_count += 1
            error_type = f"{status_code // 100}xx"
            self.errors_by_type[error_type] += 1

        log_data = {
            "method": method,
            "path": path,
            "status": status_code,
            "duration_ms": round(duration * 1000, 2),
            "ip": ip,
            "user_agent": user_agent,
        }

        if status_code >= 400:
            logger.warning(f"Request failed: {log_data}")
        else:
            logger.info(f"Request: {log_data}")

    def get_stats(self) -> Dict[str, Any]:
        """Get request statistics"""
        avg_duration = self.total_duration / self.request_count if self.request_count > 0 else 0

        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "avg_duration_ms": round(avg_duration * 1000, 2),
            "requests_by_endpoint": dict(self.requests_by_endpoint),
            "errors_by_type": dict(self.errors_by_type),
        }


# Decorator for rate limiting
def rate_limit(
    rate_limiter: RateLimiter,
    get_identifier: Callable = lambda request: request.remote,
):
    """
    Rate limiting decorator

    Usage:
        @rate_limit(rate_limiter)
        async def my_handler(request):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            identifier = get_identifier(request)
            allowed, info = rate_limiter.is_allowed(identifier)

            if not allowed:
                from aiohttp import web

                return web.Response(
                    status=429,
                    text=f"Rate limit exceeded. Retry after {info['retry_after']} seconds.",
                    headers={"Retry-After": str(info["retry_after"])},
                )

            # Add rate limit headers
            response = await func(request, *args, **kwargs)

            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Remaining-Minute"] = str(
                    info.get("requests_remaining_minute", 0)
                )
                response.headers["X-RateLimit-Remaining-Hour"] = str(
                    info.get("requests_remaining_hour", 0)
                )

            return response

        return wrapper

    return decorator


# Global instances (can be initialized from config)
_rate_limiter: Optional[RateLimiter] = None
_request_cache: Optional[RequestCache] = None
_request_logger: Optional[RequestLogger] = None


def init_middleware(
    rate_limit_rpm: int = 60,
    rate_limit_rph: int = 1000,
    cache_ttl: int = 300,
):
    """Initialize middleware components"""
    global _rate_limiter, _request_cache, _request_logger

    _rate_limiter = RateLimiter(
        requests_per_minute=rate_limit_rpm, requests_per_hour=rate_limit_rph
    )
    _request_cache = RequestCache(ttl_seconds=cache_ttl)
    _request_logger = RequestLogger()

    logger.info("Middleware initialized")


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    if _rate_limiter is None:
        raise RuntimeError("Middleware not initialized. Call init_middleware() first.")
    return _rate_limiter


def get_request_cache() -> RequestCache:
    """Get global request cache instance"""
    if _request_cache is None:
        raise RuntimeError("Middleware not initialized. Call init_middleware() first.")
    return _request_cache


def get_request_logger() -> RequestLogger:
    """Get global request logger instance"""
    if _request_logger is None:
        raise RuntimeError("Middleware not initialized. Call init_middleware() first.")
    return _request_logger
