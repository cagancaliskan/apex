"""
Environment-based Settings using Pydantic BaseSettings.

This module provides centralized configuration management with:
- Environment variable loading
- .env file support
- Type validation
- Default values

Usage:
    from rsw.config.settings import get_settings
    settings = get_settings()
    print(settings.cors_origins)
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    Variable names are case-insensitive and prefixed with RSW_.

    Example:
        RSW_API_HOST=0.0.0.0 python run.py
    """

    # App Info
    app_name: str = "Race Strategy Workbench"
    app_version: str = "1.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    # API Server
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    cors_allow_credentials: bool = True

    # Security
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Simulation
    default_simulation_speed: float = 1.0
    max_simulation_speed: float = 100.0
    simulation_frame_rate: int = 50  # FPS

    # Data Sources
    openf1_base_url: str = "https://api.openf1.org/v1"
    openf1_timeout_seconds: float = 10.0
    openf1_max_retries: int = 3

    # Cache
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    fastf1_cache_dir: str = ".fastf1-cache"

    # Logging
    log_level: str = "INFO"
    log_to_file: bool = False
    log_file_path: str = "logs/rsw.log"

    # Database (future use)
    database_url: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="RSW_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses LRU cache to ensure settings are only loaded once.

    Returns:
        Settings: The application settings
    """
    return Settings()


# Convenience function for common access patterns
def get_api_url() -> str:
    """Get the full API base URL."""
    settings = get_settings()
    return f"http://{settings.api_host}:{settings.api_port}"
