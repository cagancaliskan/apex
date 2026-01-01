"""
Health check endpoints.

Provides liveness and readiness probes for container orchestration.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel

from rsw.logging_config import get_logger
from rsw.runtime_config import get_config

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    environment: str
    timestamp: str
    checks: dict[str, dict[str, Any]]


class ComponentHealth(BaseModel):
    """Individual component health."""

    status: str
    latency_ms: float | None = None
    message: str | None = None


async def check_database() -> ComponentHealth:
    """Check database connectivity."""
    import time

    try:
        from rsw.db import get_engine

        start = time.time()
        engine = await get_engine()

        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000

        return ComponentHealth(
            status="healthy",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return ComponentHealth(
            status="unhealthy",
            message=str(e),
        )


async def check_redis() -> ComponentHealth:
    """Check Redis connectivity."""
    import time

    try:
        import redis.asyncio as redis

        config = get_config()
        start = time.time()
        client = redis.from_url(config.database.redis_url)
        await client.ping()
        await client.close()
        latency = (time.time() - start) * 1000

        return ComponentHealth(
            status="healthy",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        # Redis is optional, so degrade gracefully
        return ComponentHealth(
            status="degraded",
            message=f"Redis unavailable: {e}",
        )


async def check_openf1() -> ComponentHealth:
    """Check OpenF1 API connectivity."""
    import time

    import httpx

    try:
        config = get_config()

        start = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{config.api.openf1_base_url}/sessions?limit=1")
            response.raise_for_status()

        latency = (time.time() - start) * 1000

        return ComponentHealth(
            status="healthy",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return ComponentHealth(
            status="degraded",
            message=f"OpenF1 API unavailable: {e}",
        )


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """
    Comprehensive health check endpoint.

    Checks all dependencies and returns overall status.
    """
    config = get_config()
    # Run all health checks
    db_health = await check_database()
    redis_health = await check_redis()
    openf1_health = await check_openf1()

    checks = {
        "database": db_health.model_dump(),
        "redis": redis_health.model_dump(),
        "openf1": openf1_health.model_dump(),
    }

    # Determine overall status
    statuses = [db_health.status, redis_health.status, openf1_health.status]

    if "unhealthy" in statuses:
        overall_status = "unhealthy"
    elif "degraded" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthStatus(
        status=overall_status,
        version="1.0.0",
        environment=config.environment,
        timestamp=datetime.now(UTC).isoformat(),
        checks=checks,
    )


@router.get("/health/live")
async def liveness_probe() -> dict:
    """
    Kubernetes liveness probe.

    Returns 200 if the application is running.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe(response: Response) -> dict:
    """
    Kubernetes readiness probe.

    Returns 200 if the application is ready to serve traffic.
    Returns 503 if not ready.
    """
    # Check critical dependencies
    db_health = await check_database()

    if db_health.status == "unhealthy":
        response.status_code = 503
        return {"status": "not_ready", "reason": "Database unavailable"}

    return {"status": "ready"}


@router.get("/version")
async def version() -> dict:
    """Get application version information."""
    config = get_config()

    return {
        "version": "1.0.0",
        "environment": config.environment,
        "python": "3.11",
    }
