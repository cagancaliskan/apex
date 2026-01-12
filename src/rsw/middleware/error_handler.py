"""
Global error handling middleware.

Provides consistent error responses and logging for all exceptions.
"""

import traceback
from collections.abc import Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from rsw.exceptions import RSWError
from rsw.logging_config import get_logger
from rsw.runtime_config import get_config

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler that converts exceptions to JSON responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error handling."""
        try:
            from typing import cast

            response = cast(Response, await call_next(request))
            return response

        except RSWError as e:
            # Our custom exceptions
            logger.error(
                "rsw_error",
                code=e.code,
                message=e.message,
                details=e.details,
                path=request.url.path,
            )

            status_code = self._get_status_code(e.code)
            return JSONResponse(
                status_code=status_code,
                content=e.to_dict(),
            )

        except HTTPException as e:
            # FastAPI HTTP exceptions (pass through)
            logger.warning(
                "http_error",
                status_code=e.status_code,
                detail=e.detail,
                path=request.url.path,
            )
            raise

        except Exception as e:
            # Unexpected exceptions
            config = get_config()

            logger.exception(
                "unhandled_error",
                error=str(e),
                path=request.url.path,
                method=request.method,
            )

            # In development, include stack trace
            if config.is_development:
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": str(e),
                            "traceback": traceback.format_exc().split("\n"),
                        }
                    },
                )

            # In production, hide details
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An internal error occurred",
                    }
                },
            )

    def _get_status_code(self, error_code: str) -> int:
        """Map error codes to HTTP status codes."""
        code_map = {
            # 400 Bad Request
            "INVALID_DATA": 400,
            "DATA_ERROR": 400,
            "CONFIG_ERROR": 400,
            # 401 Unauthorized
            "AUTH_ERROR": 401,
            "INVALID_TOKEN": 401,
            # 403 Forbidden
            "INSUFFICIENT_PERMISSIONS": 403,
            # 404 Not Found
            "SESSION_NOT_FOUND": 404,
            "DRIVER_NOT_FOUND": 404,
            "CACHED_SESSION_NOT_FOUND": 404,
            # 422 Unprocessable
            "INSUFFICIENT_DATA": 422,
            # 429 Too Many Requests
            "RATE_LIMIT_EXCEEDED": 429,
            # 500 Internal Server Error
            "API_ERROR": 502,
            "API_TIMEOUT": 504,
            "API_CONNECTION_ERROR": 503,
            "MODEL_ERROR": 500,
            "STRATEGY_ERROR": 500,
        }

        return code_map.get(error_code, 500)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Custom handler for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
            }
        },
        headers=getattr(exc, "headers", None),
    )
