"""
Structured logging configuration for the Race Strategy Workbench.

Uses structlog for structured, queryable logs with proper levels,
timestamps, and context.
"""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import Processor


def setup_logging(
    log_level: str = "INFO",
    log_file: str | None = None,
    json_format: bool = False,
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        json_format: If True, output JSON logs (for production)
    """
    # Set up stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        logging.getLogger().addHandler(file_handler)
    
    # Configure structlog processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if json_format:
        # Production: JSON output
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        # Development: Pretty console output
        shared_processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables to all subsequent log calls.
    
    Args:
        **kwargs: Context key-value pairs
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


# Pre-configured loggers for common modules
class Loggers:
    """Pre-configured logger instances."""
    
    @staticmethod
    def api() -> structlog.stdlib.BoundLogger:
        """Logger for API operations."""
        return get_logger("rsw.api")
    
    @staticmethod
    def ingest() -> structlog.stdlib.BoundLogger:
        """Logger for data ingestion."""
        return get_logger("rsw.ingest")
    
    @staticmethod
    def strategy() -> structlog.stdlib.BoundLogger:
        """Logger for strategy calculations."""
        return get_logger("rsw.strategy")
    
    @staticmethod
    def models() -> structlog.stdlib.BoundLogger:
        """Logger for ML models."""
        return get_logger("rsw.models")
    
    @staticmethod
    def replay() -> structlog.stdlib.BoundLogger:
        """Logger for replay system."""
        return get_logger("rsw.replay")


# Initialize with defaults on import
setup_logging()
