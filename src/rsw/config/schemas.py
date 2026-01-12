"""
Pydantic configuration schemas.
"""

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = "127.0.0.1"
    port: int = 8000
    websocket_port: int = 8765
    debug: bool = True


class PollingConfig(BaseModel):
    """Polling configuration."""

    interval_seconds: float = 2.0
    cache_ttl_seconds: float = 3.0


class UIConfig(BaseModel):
    """UI configuration."""

    refresh_ms: int = 500
    theme: str = "dark"


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    snapshot_every_n_updates: int = 10
    log_to_file: bool = False


class OpenF1Config(BaseModel):
    """OpenF1 API configuration."""

    base_url: str = "https://api.openf1.org/v1"
    timeout_seconds: float = 10.0
    max_retries: int = 3
    rate_limit_per_minute: int = 60


class AppConfig(BaseModel):
    """Main application configuration."""

    server: ServerConfig = Field(default_factory=ServerConfig)
    polling: PollingConfig = Field(default_factory=PollingConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    openf1: OpenF1Config = Field(default_factory=OpenF1Config)


class TrackConfig(BaseModel):
    """Track-specific configuration."""

    track_id: str
    name: str
    location: str
    country: str
    laps: int
    pit_loss_seconds: float
    pit_loss_sigma: float = 1.5
    sc_base_rate: float = 0.4
    vsc_base_rate: float = 0.3
    overtake_difficulty: int = 5
    drs_zones: int = 2


class MonteCarloConfig(BaseModel):
    """Monte Carlo simulation configuration."""

    simulations: int = 2000
    horizon_laps: int = 20
    random_seed: int | None = None


class PitWindowConfig(BaseModel):
    """Pit window analysis configuration."""

    candidate_laps_ahead: int = 10
    candidate_laps_behind: int = 5
    min_stint_length: int = 5
    max_stint_length: int = 40


class SafetyCarConfig(BaseModel):
    """Safety car modeling configuration."""

    sc_multiplier: float = 1.0
    vsc_multiplier: float = 1.0
    sc_lap_loss: float = 0.5
    vsc_lap_loss: float = 0.2


class PaceNoiseConfig(BaseModel):
    """Pace noise modeling configuration."""

    multiplier: float = 1.0
    traffic_delta_seconds: float = 0.5
    dirty_air_delta_seconds: float = 0.3


class DegradationConfig(BaseModel):
    """Degradation modeling configuration."""

    forgetting_factor: float = 0.95
    min_observations: int = 3
    outlier_threshold_sigma: float = 3.0
    warm_start_deg_per_lap: dict[str, float] = Field(
        default_factory=lambda: {"SOFT": 0.08, "MEDIUM": 0.05, "HARD": 0.03}
    )


class DecisionConfig(BaseModel):
    """Decision making configuration."""

    objective: str = "expected_position"
    undercut_risk_threshold: float = 0.7
    overcut_opportunity_threshold: float = 0.6
    confidence_threshold: float = 0.75


class ThresholdsConfig(BaseModel):
    """Warning thresholds configuration."""

    cliff_risk_deg_slope: float = 0.15
    high_deg_warning: float = 0.12
    undercut_window_laps: int = 3
    traffic_gap_seconds: float = 1.5


class StrategyConfig(BaseModel):
    """Strategy engine configuration."""

    monte_carlo: MonteCarloConfig = Field(default_factory=MonteCarloConfig)
    pit_window: PitWindowConfig = Field(default_factory=PitWindowConfig)
    safety_car: SafetyCarConfig = Field(default_factory=SafetyCarConfig)
    pace_noise: PaceNoiseConfig = Field(default_factory=PaceNoiseConfig)
    degradation: DegradationConfig = Field(default_factory=DegradationConfig)
    decision: DecisionConfig = Field(default_factory=DecisionConfig)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
