# ============================================================================
# F1 Race Strategy Workbench - Dockerfile
# ============================================================================
# Multi-stage build for optimized production image

# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Production image
FROM python:3.11-slim as production

LABEL maintainer="RSW Team"
LABEL version="1.0.0"
LABEL description="F1 Race Strategy Workbench"

# Create non-root user
RUN groupadd -r rsw && useradd -r -g rsw rsw

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy application code
COPY src/ ./src/
COPY configs/ ./configs/
COPY scripts/ ./scripts/

# Create directories
RUN mkdir -p /app/data/sessions /app/logs && \
    chown -R rsw:rsw /app

# Set environment
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV RSW_ENVIRONMENT=production
ENV RSW_LOG_FORMAT=json

# Switch to non-root user
USER rsw

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "rsw.main:app", "--host", "0.0.0.0", "--port", "8000"]
