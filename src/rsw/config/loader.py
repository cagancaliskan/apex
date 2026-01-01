"""
Configuration file loaders.
"""

from pathlib import Path
from typing import Any

import yaml

from .schemas import AppConfig, TrackConfig, StrategyConfig


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents."""
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def get_config_dir() -> Path:
    """Get the configs directory path."""
    # Look relative to this file, then go up to project root
    current = Path(__file__).resolve()
    project_root = current.parent.parent.parent.parent  # src/rsw/config -> project root
    return project_root / "configs"


def load_app_config(path: Path | None = None) -> AppConfig:
    """Load application configuration from YAML file."""
    if path is None:
        path = get_config_dir() / "app.yaml"
    
    if not path.exists():
        return AppConfig()
    
    data = _load_yaml(path)
    return AppConfig(**data)


def load_tracks_config(path: Path | None = None) -> dict[str, TrackConfig]:
    """Load tracks configuration from YAML file."""
    if path is None:
        path = get_config_dir() / "tracks.yaml"
    
    if not path.exists():
        return {}
    
    data = _load_yaml(path)
    tracks_data = data.get("tracks", {})
    
    return {
        track_id: TrackConfig(**track_data)
        for track_id, track_data in tracks_data.items()
    }


def load_strategy_config(path: Path | None = None) -> StrategyConfig:
    """Load strategy configuration from YAML file."""
    if path is None:
        path = get_config_dir() / "strategy.yaml"
    
    if not path.exists():
        return StrategyConfig()
    
    data = _load_yaml(path)
    return StrategyConfig(**data)
