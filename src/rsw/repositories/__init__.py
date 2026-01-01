"""
Repositories package.

Data access layer following Repository Pattern.
Separates data access from business logic.
"""

from .session_repository import SessionRepository

__all__ = ["SessionRepository"]
