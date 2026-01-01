"""
Middleware package for the Race Strategy Workbench.
"""

from .auth import (
    AuthUser,
    create_access_token,
    decode_token,
    get_current_user,
    require_auth,
    require_permission,
    require_role,
)
from .rate_limit import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitMiddleware,
    rate_limit,
)
from .error_handler import ErrorHandlerMiddleware, http_exception_handler

__all__ = [
    # Auth
    "AuthUser",
    "create_access_token",
    "decode_token",
    "get_current_user",
    "require_auth",
    "require_permission",
    "require_role",
    # Rate Limit
    "InMemoryRateLimiter",
    "RateLimitConfig",
    "RateLimitMiddleware",
    "rate_limit",
    # Error Handler
    "ErrorHandlerMiddleware",
    "http_exception_handler",
]
