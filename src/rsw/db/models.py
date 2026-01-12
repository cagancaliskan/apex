"""
Database models and connection management.

Uses SQLAlchemy 2.0 async for PostgreSQL.
"""

from collections.abc import AsyncGenerator, Callable
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from rsw.runtime_config import get_config


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# ============================================================================
# Session Models
# ============================================================================


class SessionModel(Base):
    """Cached F1 session."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_key: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    session_name: Mapped[str] = mapped_column(String(50))
    session_type: Mapped[str | None] = mapped_column(String(20))
    country_name: Mapped[str | None] = mapped_column(String(100))
    circuit_short_name: Mapped[str | None] = mapped_column(String(50))
    year: Mapped[int] = mapped_column(Integer, index=True)
    date_start: Mapped[datetime | None] = mapped_column(DateTime)
    date_end: Mapped[datetime | None] = mapped_column(DateTime)

    # Cache metadata
    cached_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    cache_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    drivers: Mapped[list["DriverModel"]] = relationship(back_populates="session")
    laps: Mapped[list["LapModel"]] = relationship(back_populates="session")


class DriverModel(Base):
    """Driver in a session."""

    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    driver_number: Mapped[int] = mapped_column(Integer, index=True)
    name_acronym: Mapped[str] = mapped_column(String(10))
    full_name: Mapped[str | None] = mapped_column(String(100))
    team_name: Mapped[str | None] = mapped_column(String(100))
    team_colour: Mapped[str | None] = mapped_column(String(10))

    # Relationship
    session: Mapped["SessionModel"] = relationship(back_populates="drivers")


class LapModel(Base):
    """Lap time record."""

    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    driver_number: Mapped[int] = mapped_column(Integer, index=True)
    lap_number: Mapped[int] = mapped_column(Integer)
    lap_duration: Mapped[float | None] = mapped_column(Float)
    sector_1_time: Mapped[float | None] = mapped_column(Float)
    sector_2_time: Mapped[float | None] = mapped_column(Float)
    sector_3_time: Mapped[float | None] = mapped_column(Float)
    is_pit_out_lap: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pit_in_lap: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship
    session: Mapped["SessionModel"] = relationship(back_populates="laps")


class StintModel(Base):
    """Tyre stint record."""

    __tablename__ = "stints"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    driver_number: Mapped[int] = mapped_column(Integer, index=True)
    stint_number: Mapped[int] = mapped_column(Integer)
    compound: Mapped[str | None] = mapped_column(String(20))
    lap_start: Mapped[int] = mapped_column(Integer)
    lap_end: Mapped[int | None] = mapped_column(Integer)
    tyre_age_at_start: Mapped[int] = mapped_column(Integer, default=0)


class PitStopModel(Base):
    """Pit stop record."""

    __tablename__ = "pit_stops"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    driver_number: Mapped[int] = mapped_column(Integer, index=True)
    lap_number: Mapped[int] = mapped_column(Integer)
    pit_duration: Mapped[float | None] = mapped_column(Float)


class RaceControlModel(Base):
    """Race control message."""

    __tablename__ = "race_control"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    lap_number: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(50))
    flag: Mapped[str | None] = mapped_column(String(20))
    message: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime)


# ============================================================================
# Database Connection
# ============================================================================

_engine: AsyncEngine | None = None


_session_factory: Callable[[], AsyncSession] | None = None


async def get_engine() -> AsyncEngine:
    """Get or create database engine."""
    global _engine
    if _engine is None:
        config = get_config()
        _engine = create_async_engine(
            config.database.postgres_url,
            pool_size=config.database.pool_size,
            max_overflow=config.database.pool_max_overflow,
            echo=config.is_development,
        )
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    global _session_factory
    if _session_factory is None:
        engine = await get_engine()
        from collections.abc import Callable
        from typing import cast

        from sqlalchemy.ext.asyncio import async_sessionmaker

        _session_factory = cast(
            Callable[[], AsyncSession],
            async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            ),
        )

    async with _session_factory() as session:
        yield session


async def init_db() -> None:
    """Initialize database tables."""
    engine = await get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
