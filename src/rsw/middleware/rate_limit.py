"""
Rate limiting middleware.

Provides request rate limiting using in-memory or Redis storage.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Any

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from rsw.logging_config import get_logger
from rsw.runtime_config import get_config

logger = get_logger(__name__)


@dataclass
class RateLimitState:
    """State for a single rate limit key."""
    tokens: float
    last_update: float
    
    
@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    
    # Per-endpoint overrides
    endpoint_limits: dict[str, int] = field(default_factory=dict)


class InMemoryRateLimiter:
    """
    In-memory token bucket rate limiter.
    
    Suitable for single-instance deployments.
    For multi-instance, use RedisRateLimiter.
    """
    
    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self._buckets: dict[str, RateLimitState] = defaultdict(
            lambda: RateLimitState(
                tokens=float(self.config.burst_size),
                last_update=time.time(),
            )
        )
    
    def _get_key(self, request: Request) -> str:
        """Get rate limit key from request."""
        # Use client IP as key
        client_ip = request.client.host if request.client else "unknown"
        
        # Could also include user ID if authenticated
        # user = getattr(request.state, "user", None)
        # if user:
        #     return f"{client_ip}:{user.user_id}"
        
        return client_ip
    
    def _refill_tokens(self, state: RateLimitState) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - state.last_update
        
        # Tokens per second
        rate = self.config.requests_per_minute / 60.0
        
        # Add tokens for elapsed time
        state.tokens = min(
            self.config.burst_size,
            state.tokens + elapsed * rate,
        )
        state.last_update = now
    
    def check_rate_limit(
        self,
        request: Request,
        cost: int = 1,
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit.
        
        Args:
            request: FastAPI request
            cost: Number of tokens to consume
        
        Returns:
            Tuple of (allowed, headers)
        """
        key = self._get_key(request)
        state = self._buckets[key]
        
        # Refill tokens
        self._refill_tokens(state)
        
        # Check endpoint-specific limit
        endpoint = request.url.path
        limit = self.config.endpoint_limits.get(
            endpoint,
            self.config.requests_per_minute,
        )
        
        # Calculate headers
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, int(state.tokens - cost))),
            "X-RateLimit-Reset": str(int(state.last_update + 60)),
        }
        
        if state.tokens >= cost:
            state.tokens -= cost
            return True, headers
        
        # Rate limited
        retry_after = int((cost - state.tokens) / (limit / 60.0))
        headers["Retry-After"] = str(retry_after)
        
        logger.warning(
            "rate_limit_exceeded",
            client=key,
            endpoint=endpoint,
            retry_after=retry_after,
        )
        
        return False, headers


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    """
    
    def __init__(
        self,
        app: Any,
        limiter: InMemoryRateLimiter | None = None,
        exclude_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.limiter = limiter or InMemoryRateLimiter()
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            from typing import cast
            return cast(Response, await call_next(request))
        
        # Check rate limit
        allowed, headers = self.limiter.check_rate_limit(request)
        
        if not allowed:
            return Response(
                content='{"error": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers=headers,
            )
        
        from typing import cast
        # Process request
        response = cast(Response, await call_next(request))
        
        # Add rate limit headers
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


def rate_limit(
    requests_per_minute: int = 60,
    burst_size: int = 10,
) -> Callable:
    """
    Decorator for endpoint-specific rate limiting.
    
    Args:
        requests_per_minute: Maximum requests per minute
        burst_size: Maximum burst size
    
    Returns:
        Decorator function
    """
    limiter = InMemoryRateLimiter(
        RateLimitConfig(
            requests_per_minute=requests_per_minute,
            burst_size=burst_size,
        )
    )
    
    def decorator(func: Callable) -> Callable:
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            allowed, headers = limiter.check_rate_limit(request)
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers=headers,
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator
