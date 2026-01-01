"""
Session Repository - data access for sessions.

Follows Repository Pattern for Separation of Concerns.
"""

from typing import Any, cast

from rsw.interfaces import IRepository
from rsw.db.models import SessionModel
from rsw.logging_config import get_logger

logger = get_logger(__name__)


class SessionRepository(IRepository[SessionModel]):
    """
    Repository for session data access.
    
    Follows:
    - SRP: Only handles session persistence
    - Separation of Concerns: Data access separate from business logic
    - DIP: Can swap database implementations
    """
    
    def __init__(self, session_factory: Any) -> None:
        """
        Initialize with database session factory.
        
        Args:
            session_factory: SQLAlchemy session factory
        """
        self._session_factory = session_factory
    
    async def get_by_id(self, id: int) -> SessionModel | None:
        """
        Get session by ID.
        
        Args:
            id: Session database ID
            
        Returns:
            SessionModel or None if not found
        """
        async with self._session_factory() as session:
            result = await session.get(SessionModel, id)
            return cast(SessionModel | None, result)
    
    async def get_by_key(self, session_key: int) -> SessionModel | None:
        """
        Get session by session_key.
        
        Args:
            session_key: OpenF1 session key
            
        Returns:
            SessionModel or None
        """
        from sqlalchemy import select
        
        async with self._session_factory() as session:
            stmt = select(SessionModel).where(SessionModel.session_key == session_key)
            from typing import cast
            result = await session.execute(stmt)
            return cast(SessionModel | None, result.scalar_one_or_none())
    
    async def get_all(self, **filters: Any) -> list[SessionModel]:
        """
        Get all sessions matching filters.
        
        Args:
            **filters: Filter criteria (year, session_name, etc.)
            
        Returns:
            List of matching sessions
        """
        from sqlalchemy import select
        
        async with self._session_factory() as session:
            stmt = select(SessionModel)
            
            # Apply filters
            if "year" in filters:
                stmt = stmt.where(SessionModel.year == filters["year"])
            if "session_name" in filters:
                stmt = stmt.where(SessionModel.session_name == filters["session_name"])
            
            stmt = stmt.order_by(SessionModel.date_start.desc())
            
            if "limit" in filters:
                stmt = stmt.limit(filters["limit"])
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    async def create(self, entity: SessionModel) -> SessionModel:
        """
        Create a new session.
        
        Args:
            entity: Session to create
            
        Returns:
            Created session with ID
        """
        async with self._session_factory() as session:
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            
            logger.info("session_created", session_key=entity.session_key)
            return entity
    
    async def update(self, entity: SessionModel) -> SessionModel:
        """
        Update existing session.
        
        Args:
            entity: Session with updates
            
        Returns:
            Updated session
        """
        async with self._session_factory() as session:
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            
            logger.info("session_updated", session_key=entity.session_key)
            return entity
    
    async def delete(self, id: int) -> bool:
        """
        Delete session by ID.
        
        Args:
            id: Session ID to delete
            
        Returns:
            True if deleted
        """
        async with self._session_factory() as session:
            entity = await session.get(SessionModel, id)
            if entity:
                await session.delete(entity)
                await session.commit()
                logger.info("session_deleted", id=id)
                return True
            return False
    
    async def exists(self, session_key: int) -> bool:
        """
        Check if session exists.
        
        Args:
            session_key: Session key to check
            
        Returns:
            True if exists
        """
        result = await self.get_by_key(session_key)
        return result is not None
