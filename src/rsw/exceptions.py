"""
Custom exceptions for the Race Strategy Workbench.

Provides structured exception hierarchy for proper error handling
and meaningful error messages throughout the application.
"""

from typing import Any, Optional


class RSWError(Exception):
    """Base exception for all RSW errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "RSW_ERROR",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


# ============================================================================
# API Errors
# ============================================================================

class APIError(RSWError):
    """Error communicating with external APIs."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        endpoint: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="API_ERROR",
            details={"status_code": status_code, "endpoint": endpoint},
        )
        self.status_code = status_code
        self.endpoint = endpoint


class RateLimitError(APIError):
    """Rate limit exceeded on external API."""
    
    def __init__(
        self,
        retry_after: Optional[int] = None,
        endpoint: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after}s",
            status_code=429,
            endpoint=endpoint,
        )
        self.retry_after = retry_after
        self.code = "RATE_LIMIT_EXCEEDED"


class APITimeoutError(APIError):
    """Request to external API timed out."""
    
    def __init__(self, endpoint: Optional[str] = None, timeout: float = 30.0) -> None:
        super().__init__(
            message=f"Request timed out after {timeout}s",
            status_code=None,
            endpoint=endpoint,
        )
        self.timeout = timeout
        self.code = "API_TIMEOUT"


class APIConnectionError(APIError):
    """Failed to connect to external API."""
    
    def __init__(self, endpoint: Optional[str] = None) -> None:
        super().__init__(
            message="Failed to connect to API",
            status_code=None,
            endpoint=endpoint,
        )
        self.code = "API_CONNECTION_ERROR"


# ============================================================================
# Data Errors
# ============================================================================

class DataError(RSWError):
    """Error with data processing or validation."""
    
    def __init__(self, message: str, field: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="DATA_ERROR",
            details={"field": field} if field else {},
        )


class SessionNotFoundError(DataError):
    """Requested session was not found."""
    
    def __init__(self, session_key: int) -> None:
        super().__init__(
            message=f"Session {session_key} not found",
            field="session_key",
        )
        self.session_key = session_key
        self.code = "SESSION_NOT_FOUND"


class DriverNotFoundError(DataError):
    """Requested driver was not found."""
    
    def __init__(self, driver_number: int, session_key: Optional[int] = None) -> None:
        super().__init__(
            message=f"Driver {driver_number} not found",
            field="driver_number",
        )
        self.driver_number = driver_number
        self.session_key = session_key
        self.code = "DRIVER_NOT_FOUND"


class InvalidDataError(DataError):
    """Data failed validation."""
    
    def __init__(self, message: str, field: str, value: Any = None) -> None:
        super().__init__(message=message, field=field)
        self.value = value
        self.code = "INVALID_DATA"
        self.details["value"] = value


# ============================================================================
# Strategy Errors
# ============================================================================

class StrategyError(RSWError):
    """Error in strategy calculation."""
    
    def __init__(self, message: str, driver_number: Optional[int] = None) -> None:
        super().__init__(
            message=message,
            code="STRATEGY_ERROR",
            details={"driver_number": driver_number} if driver_number else {},
        )


class InsufficientDataError(StrategyError):
    """Not enough data for strategy calculation."""
    
    def __init__(
        self,
        message: str = "Insufficient data for calculation",
        required: int = 0,
        available: int = 0,
    ) -> None:
        super().__init__(message=message)
        self.required = required
        self.available = available
        self.code = "INSUFFICIENT_DATA"
        self.details.update({"required": required, "available": available})


class ModelError(StrategyError):
    """Error in ML model prediction."""
    
    def __init__(self, message: str, model_name: Optional[str] = None) -> None:
        super().__init__(message=message)
        self.model_name = model_name
        self.code = "MODEL_ERROR"
        if model_name:
            self.details["model_name"] = model_name


# ============================================================================
# Authentication Errors
# ============================================================================

class AuthError(RSWError):
    """Authentication/authorization error."""
    
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message=message, code="AUTH_ERROR")


class InvalidTokenError(AuthError):
    """Invalid or expired authentication token."""
    
    def __init__(self, reason: str = "Token is invalid or expired") -> None:
        super().__init__(message=reason)
        self.code = "INVALID_TOKEN"


class InsufficientPermissionsError(AuthError):
    """User lacks required permissions."""
    
    def __init__(self, required_permission: str) -> None:
        super().__init__(message=f"Missing required permission: {required_permission}")
        self.required_permission = required_permission
        self.code = "INSUFFICIENT_PERMISSIONS"


# ============================================================================
# Replay Errors
# ============================================================================

class ReplayError(RSWError):
    """Error during replay playback."""
    
    def __init__(self, message: str, session_key: Optional[int] = None) -> None:
        super().__init__(
            message=message,
            code="REPLAY_ERROR",
            details={"session_key": session_key} if session_key else {},
        )


class CachedSessionNotFoundError(ReplayError):
    """Cached session file not found."""
    
    def __init__(self, session_key: int, path: Optional[str] = None) -> None:
        super().__init__(
            message=f"Cached session {session_key} not found",
            session_key=session_key,
        )
        self.path = path
        self.code = "CACHED_SESSION_NOT_FOUND"


class NoActiveReplayError(ReplayError):
    """No replay is currently active."""
    
    def __init__(self) -> None:
        super().__init__(message="No active replay session")
        self.code = "NO_ACTIVE_REPLAY"


# ============================================================================
# Configuration Errors
# ============================================================================

class ConfigError(RSWError):
    """Configuration error."""
    
    def __init__(self, message: str, config_key: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            details={"config_key": config_key} if config_key else {},
        )


class MissingConfigError(ConfigError):
    """Required configuration is missing."""
    
    def __init__(self, config_key: str) -> None:
        super().__init__(
            message=f"Missing required configuration: {config_key}",
            config_key=config_key,
        )
        self.code = "MISSING_CONFIG"
