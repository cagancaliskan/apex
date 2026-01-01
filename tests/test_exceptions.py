"""
Exception handling tests.
"""

import pytest
from rsw.exceptions import (
    RSWError,
    APIError,
    RateLimitError,
    APITimeoutError,
    SessionNotFoundError,
    DriverNotFoundError,
    InvalidDataError,
    InsufficientDataError,
    InvalidTokenError,
    CachedSessionNotFoundError,
)


class TestRSWError:
    """Tests for base exception class."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = RSWError("Something went wrong")
        
        assert str(error) == "Something went wrong"
        assert error.code == "RSW_ERROR"
        assert error.details == {}
    
    def test_error_with_details(self):
        """Test error with details."""
        error = RSWError(
            "Error with context",
            code="CUSTOM_CODE",
            details={"key": "value"},
        )
        
        assert error.code == "CUSTOM_CODE"
        assert error.details["key"] == "value"
    
    def test_to_dict(self):
        """Test error serialization."""
        error = RSWError("Test error", code="TEST", details={"id": 123})
        result = error.to_dict()
        
        assert result["error"]["code"] == "TEST"
        assert result["error"]["message"] == "Test error"
        assert result["error"]["details"]["id"] == 123


class TestAPIErrors:
    """Tests for API-related exceptions."""
    
    def test_api_error(self):
        """Test API error."""
        error = APIError("Connection failed", status_code=500, endpoint="/api/test")
        
        assert error.status_code == 500
        assert error.endpoint == "/api/test"
    
    def test_rate_limit_error(self):
        """Test rate limit error."""
        error = RateLimitError(retry_after=30, endpoint="/api/sessions")
        
        assert error.code == "RATE_LIMIT_EXCEEDED"
        assert error.retry_after == 30
        assert "30" in error.message
    
    def test_timeout_error(self):
        """Test timeout error."""
        error = APITimeoutError(endpoint="/api/slow", timeout=30.0)
        
        assert error.code == "API_TIMEOUT"
        assert error.timeout == 30.0


class TestDataErrors:
    """Tests for data-related exceptions."""
    
    def test_session_not_found(self):
        """Test session not found error."""
        error = SessionNotFoundError(session_key=9999)
        
        assert error.code == "SESSION_NOT_FOUND"
        assert error.session_key == 9999
        assert "9999" in error.message
    
    def test_driver_not_found(self):
        """Test driver not found error."""
        error = DriverNotFoundError(driver_number=99, session_key=9158)
        
        assert error.code == "DRIVER_NOT_FOUND"
        assert error.driver_number == 99
    
    def test_invalid_data(self):
        """Test invalid data error."""
        error = InvalidDataError(
            message="Value out of range",
            field="lap_time",
            value=-5.0,
        )
        
        assert error.code == "INVALID_DATA"
        assert error.details["field"] == "lap_time"
        assert error.details["value"] == -5.0


class TestStrategyErrors:
    """Tests for strategy-related exceptions."""
    
    def test_insufficient_data(self):
        """Test insufficient data error."""
        error = InsufficientDataError(
            message="Need more laps",
            required=5,
            available=2,
        )
        
        assert error.code == "INSUFFICIENT_DATA"
        assert error.required == 5
        assert error.available == 2


class TestAuthErrors:
    """Tests for authentication exceptions."""
    
    def test_invalid_token(self):
        """Test invalid token error."""
        error = InvalidTokenError("Token expired")
        
        assert error.code == "INVALID_TOKEN"


class TestReplayErrors:
    """Tests for replay exceptions."""
    
    def test_cached_session_not_found(self):
        """Test cached session not found."""
        error = CachedSessionNotFoundError(
            session_key=9158,
            path="/data/sessions/9158.json",
        )
        
        assert error.code == "CACHED_SESSION_NOT_FOUND"
        assert error.path == "/data/sessions/9158.json"
