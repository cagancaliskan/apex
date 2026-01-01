"""
Runtime configuration with environment variable support.

Uses pydantic-settings for type-safe configuration with validation.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseSettings):
    """Server configuration."""
    
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    workers: int = 1
    
    model_config = SettingsConfigDict(env_prefix="RSW_SERVER_")


class APIConfig(BaseSettings):
    """External API configuration."""
    
    # OpenF1
    openf1_base_url: str = "https://api.openf1.org/v1"
    openf1_timeout: int = 30
    openf1_retry_attempts: int = 3
    openf1_retry_delay: float = 1.0
    
    model_config = SettingsConfigDict(env_prefix="RSW_API_")


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    
    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "rsw"
    postgres_password: str = ""
    postgres_db: str = "rsw"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    
    # Connection pool
    pool_size: int = 5
    pool_max_overflow: int = 10
    
    model_config = SettingsConfigDict(env_prefix="RSW_DB_")
    
    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        auth = f"{self.postgres_user}:{self.postgres_password}@" if self.postgres_password else f"{self.postgres_user}@"
        return f"postgresql+asyncpg://{auth}{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


class AuthConfig(BaseSettings):
    """Authentication configuration."""
    
    enabled: bool = False
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours
    api_key_header: str = "X-API-Key"
    
    model_config = SettingsConfigDict(env_prefix="RSW_AUTH_")


class StrategyConfig(BaseSettings):
    """Strategy engine configuration."""
    
    # RLS Model
    rls_forgetting_factor: float = Field(default=0.95, ge=0.0, le=1.0)
    rls_initial_covariance: float = 1000.0
    
    # Monte Carlo
    monte_carlo_simulations: int = Field(default=500, ge=100, le=10000)
    safety_car_probability: float = Field(default=0.3, ge=0.0, le=1.0)
    
    # Pit Window
    min_stint_laps: int = 10
    default_pit_loss: float = 22.0
    
    model_config = SettingsConfigDict(env_prefix="RSW_STRATEGY_")


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["console", "json"] = "console"
    file: str | None = None
    
    model_config = SettingsConfigDict(env_prefix="RSW_LOG_")


class PollingConfig(BaseSettings):
    """Polling configuration."""
    
    interval: float = Field(default=0.5, ge=0.1, le=60.0)
    max_retries: int = 3
    batch_size: int = 100
    
    model_config = SettingsConfigDict(env_prefix="RSW_POLLING_")


class RuntimeConfig(BaseSettings):
    """Complete runtime configuration."""
    
    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    
    # Sub-configs
    server: ServerConfig = Field(default_factory=ServerConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    polling: PollingConfig = Field(default_factory=PollingConfig)
    
    # Paths
    data_dir: Path = Path("data")
    sessions_dir: Path = Path("data/sessions")
    logs_dir: Path = Path("logs")
    
    model_config = SettingsConfigDict(
        env_prefix="RSW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    @field_validator("data_dir", "sessions_dir", "logs_dir", mode="before")
    @classmethod
    def ensure_path(cls, v: str | Path) -> Path:
        """Convert string to Path."""
        return Path(v) if isinstance(v, str) else v
    
    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


@lru_cache
def get_config() -> RuntimeConfig:
    """
    Get cached runtime configuration.
    
    Configuration is loaded once and cached for the application lifetime.
    
    Returns:
        RuntimeConfig instance
    """
    config = RuntimeConfig()
    config.ensure_directories()
    return config


# Convenience alias
config = get_config()
