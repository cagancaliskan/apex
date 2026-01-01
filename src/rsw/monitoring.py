"""
Prometheus metrics and monitoring.

Exposes application metrics for observability.
"""

import time
from functools import wraps
from typing import Callable

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from rsw.runtime_config import get_config

# ============================================================================
# Application Info
# ============================================================================

APP_INFO = Info("rsw", "Race Strategy Workbench application info")
APP_INFO.info({
    "version": "1.0.0",
    "environment": get_config().environment,
})

# ============================================================================
# HTTP Metrics
# ============================================================================

HTTP_REQUESTS_TOTAL = Counter(
    "rsw_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "rsw_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "rsw_http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"],
)

# ============================================================================
# WebSocket Metrics
# ============================================================================

WEBSOCKET_CONNECTIONS = Gauge(
    "rsw_websocket_connections_active",
    "Number of active WebSocket connections",
)

WEBSOCKET_MESSAGES_SENT = Counter(
    "rsw_websocket_messages_sent_total",
    "Total WebSocket messages sent",
)

WEBSOCKET_MESSAGES_RECEIVED = Counter(
    "rsw_websocket_messages_received_total",
    "Total WebSocket messages received",
)

# ============================================================================
# API Client Metrics
# ============================================================================

OPENF1_REQUESTS_TOTAL = Counter(
    "rsw_openf1_requests_total",
    "Total requests to OpenF1 API",
    ["endpoint", "status"],
)

OPENF1_REQUEST_DURATION = Histogram(
    "rsw_openf1_request_duration_seconds",
    "OpenF1 API request duration",
    ["endpoint"],
)

OPENF1_CACHE_HITS = Counter(
    "rsw_openf1_cache_hits_total",
    "OpenF1 cache hits",
)

OPENF1_CACHE_MISSES = Counter(
    "rsw_openf1_cache_misses_total",
    "OpenF1 cache misses",
)

# ============================================================================
# Strategy Metrics
# ============================================================================

STRATEGY_CALCULATIONS = Counter(
    "rsw_strategy_calculations_total",
    "Total strategy calculations",
    ["driver_number", "recommendation"],
)

STRATEGY_CALCULATION_DURATION = Histogram(
    "rsw_strategy_calculation_duration_seconds",
    "Strategy calculation duration",
)

MONTE_CARLO_SIMULATIONS = Counter(
    "rsw_monte_carlo_simulations_total",
    "Total Monte Carlo simulations run",
)

# ============================================================================
# ML Model Metrics
# ============================================================================

MODEL_PREDICTIONS = Counter(
    "rsw_model_predictions_total",
    "Total model predictions",
    ["model_type"],
)

MODEL_PREDICTION_DURATION = Histogram(
    "rsw_model_prediction_duration_seconds",
    "Model prediction duration",
    ["model_type"],
)

MODEL_UPDATES = Counter(
    "rsw_model_updates_total",
    "Total model updates",
    ["model_type"],
)

# ============================================================================
# Session Metrics
# ============================================================================

ACTIVE_SESSIONS = Gauge(
    "rsw_active_sessions",
    "Number of active race sessions being tracked",
)

LAPS_PROCESSED = Counter(
    "rsw_laps_processed_total",
    "Total laps processed",
)

DRIVERS_TRACKED = Gauge(
    "rsw_drivers_tracked",
    "Number of drivers currently being tracked",
)

# ============================================================================
# Middleware
# ============================================================================

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        endpoint = self._normalize_path(request.url.path)
        
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception as e:
            status = "500"
            raise
        finally:
            duration = time.time() - start_time
            
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status=status,
            ).inc()
            
            HTTP_REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)
            
            HTTP_REQUESTS_IN_PROGRESS.labels(
                method=method,
                endpoint=endpoint,
            ).dec()
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path to avoid high cardinality."""
        # Replace IDs with placeholders
        parts = path.split("/")
        normalized = []
        
        for part in parts:
            if part.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)
        
        return "/".join(normalized)


# ============================================================================
# Metrics Endpoint
# ============================================================================

async def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# ============================================================================
# Decorators
# ============================================================================

def track_duration(histogram: Histogram, labels: dict | None = None):
    """Decorator to track function duration."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start
                if labels:
                    histogram.labels(**labels).observe(duration)
                else:
                    histogram.observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                if labels:
                    histogram.labels(**labels).observe(duration)
                else:
                    histogram.observe(duration)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
