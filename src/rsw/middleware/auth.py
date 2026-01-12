"""
Authentication and authorization middleware.

Provides JWT-based authentication and API key validation.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from rsw.exceptions import InvalidTokenError
from rsw.logging_config import get_logger
from rsw.runtime_config import get_config

logger = get_logger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthUser:
    """Authenticated user information."""

    def __init__(
        self,
        user_id: str,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
    ) -> None:
        self.user_id = user_id
        self.roles = roles or []
        self.permissions = permissions or []

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions or "admin" in self.roles

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles


def create_access_token(
    user_id: str,
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User identifier
        roles: User roles
        permissions: User permissions
        expires_delta: Token expiration time

    Returns:
        JWT token string
    """
    config = get_config()

    if expires_delta is None:
        expires_delta = timedelta(minutes=config.auth.jwt_expire_minutes)

    expire = datetime.now(UTC) + expires_delta

    payload = {
        "sub": user_id,
        "roles": roles or [],
        "permissions": permissions or [],
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    token = jwt.encode(
        payload,
        config.auth.jwt_secret,
        algorithm=config.auth.jwt_algorithm,
    )

    logger.info("token_created", user_id=user_id, expires=expire.isoformat())
    return token


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        InvalidTokenError: If token is invalid or expired
    """
    config = get_config()

    try:
        from typing import cast

        payload = jwt.decode(
            token,
            config.auth.jwt_secret,
            algorithms=[config.auth.jwt_algorithm],
        )
        return cast(dict[str, Any], payload)
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {e}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    api_key: str | None = Security(api_key_header),
) -> AuthUser | None:
    """
    Get current authenticated user from request.

    Supports both JWT Bearer tokens and API keys.

    Args:
        credentials: Bearer token credentials
        api_key: API key from header

    Returns:
        AuthUser if authenticated, None if auth is disabled

    Raises:
        HTTPException: If authentication fails
    """
    config = get_config()

    # Skip auth if disabled
    if not config.auth.enabled:
        return None

    # Try JWT token first
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            return AuthUser(
                user_id=payload["sub"],
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
            )
        except InvalidTokenError as e:
            logger.warning("invalid_token", error=str(e))
            raise HTTPException(status_code=401, detail=str(e))

    # Try API key
    if api_key:
        # In production, validate against stored API keys
        # For now, accept any non-empty key in dev mode
        if config.is_development:
            return AuthUser(user_id=f"api_key_{api_key[:8]}", roles=["api_user"])

        # Production: validate against database
        # user = await validate_api_key(api_key)
        # if user:
        #     return user

    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_auth(
    user: AuthUser | None = Depends(get_current_user),
) -> AuthUser:
    """
    Dependency that requires authentication.

    Raises:
        HTTPException: If not authenticated
    """
    config = get_config()

    if not config.auth.enabled:
        return AuthUser(user_id="anonymous", roles=["user"])

    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    return user


def require_permission(permission: str) -> Callable[[AuthUser], Awaitable[AuthUser]]:
    """
    Factory for permission-checking dependencies.

    Args:
        permission: Required permission

    Returns:
        Dependency function
    """

    async def check_permission(user: AuthUser = Depends(require_auth)) -> AuthUser:
        if not user.has_permission(permission):
            logger.warning(
                "permission_denied",
                user_id=user.user_id,
                required=permission,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permission: {permission}",
            )
        return user

    return check_permission


def require_role(role: str) -> Callable[[AuthUser], Awaitable[AuthUser]]:
    """
    Factory for role-checking dependencies.

    Args:
        role: Required role

    Returns:
        Dependency function
    """

    async def check_role(user: AuthUser = Depends(require_auth)) -> AuthUser:
        if not user.has_role(role):
            logger.warning("role_denied", user_id=user.user_id, required=role)
            raise HTTPException(
                status_code=403,
                detail=f"Missing required role: {role}",
            )
        return user

    return check_role
