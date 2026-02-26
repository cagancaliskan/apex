"""
Season Learner — Cross-session driver performance aggregation.

Aggregates driver degradation profiles across all circuits in a season.
Persists to data/season_data/{year}.json for warm-starting RLS models
with driver-specific priors instead of generic compound defaults.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .track_characteristics import (
    DriverCompoundProfile,
    DriverProfile,
    TrackCharacteristics,
    TrackLearner,
)


@dataclass
class SeasonDriverProfile:
    """Season-level aggregated driver profile."""

    driver_number: int
    name: str = ""
    # Per-compound: weighted avg deg_slope and base_pace across all circuits
    compound_profiles: dict[str, DriverCompoundProfile] = field(default_factory=dict)
    overall_base_pace: float = 90.0
    circuits_count: int = 0


@dataclass
class SeasonData:
    """Complete season data with all driver profiles."""

    year: int
    driver_profiles: dict[int, SeasonDriverProfile] = field(default_factory=dict)
    circuits_analyzed: list[str] = field(default_factory=list)
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SeasonData":
        profiles_data = data.pop("driver_profiles", {})
        profiles = {}
        for drv_key, prof in profiles_data.items():
            cp_data = prof.pop("compound_profiles", {})
            cp = {k: DriverCompoundProfile(**v) for k, v in cp_data.items()}
            profiles[int(drv_key)] = SeasonDriverProfile(compound_profiles=cp, **prof)
        return cls(driver_profiles=profiles, **data)


class SeasonLearner:
    """
    Aggregates driver performance across an entire season.

    Merges DriverProfiles from each circuit's TrackCharacteristics
    into a unified SeasonDriverProfile per driver.

    Usage:
        learner = SeasonLearner()
        learner.update_from_track(track_characteristics)
        base_pace, deg_slope = learner.get_driver_priors(44, "SOFT")
    """

    def __init__(self, data_dir: Path | None = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent.parent.parent / "data" / "season_data"
        else:
            self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[int, SeasonData] = {}

    def _get_file_path(self, year: int) -> Path:
        return self.data_dir / f"{year}.json"

    def load(self, year: int) -> SeasonData:
        """Load season data, creating if not exists."""
        if year in self._cache:
            return self._cache[year]

        file_path = self._get_file_path(year)
        if file_path.exists():
            try:
                with open(file_path) as f:
                    data = json.load(f)
                season = SeasonData.from_dict(data)
                self._cache[year] = season
                return season
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

        season = SeasonData(year=year)
        self._cache[year] = season
        return season

    def save(self, season: SeasonData) -> None:
        """Save season data to disk."""
        file_path = self._get_file_path(season.year)
        season.last_updated = datetime.now().isoformat()
        with open(file_path, "w") as f:
            json.dump(season.to_dict(), f, indent=2)
        self._cache[season.year] = season

    def update_from_track(
        self,
        year: int,
        track_characteristics: TrackCharacteristics,
    ) -> SeasonData:
        """
        Merge driver profiles from a track into the season aggregate.

        Uses weighted averages across circuits so drivers who appear
        at more circuits have more reliable profiles.
        """
        season = self.load(year)
        circuit_key = track_characteristics.circuit_key

        if circuit_key in season.circuits_analyzed:
            return season

        for drv_num, track_prof in track_characteristics.driver_profiles.items():
            if drv_num in season.driver_profiles:
                sp = season.driver_profiles[drv_num]
                sp.circuits_count += 1

                # Merge per-compound profiles
                for comp, cp in track_prof.compound_profiles.items():
                    if comp in sp.compound_profiles:
                        old = sp.compound_profiles[comp]
                        total = old.sample_count + cp.sample_count
                        sp.compound_profiles[comp] = DriverCompoundProfile(
                            compound=comp,
                            avg_deg_per_lap=round(
                                (old.avg_deg_per_lap * old.sample_count
                                 + cp.avg_deg_per_lap * cp.sample_count) / total, 4),
                            avg_base_pace=round(
                                (old.avg_base_pace * old.sample_count
                                 + cp.avg_base_pace * cp.sample_count) / total, 3),
                            sample_count=total,
                        )
                    else:
                        sp.compound_profiles[comp] = DriverCompoundProfile(
                            compound=cp.compound,
                            avg_deg_per_lap=cp.avg_deg_per_lap,
                            avg_base_pace=cp.avg_base_pace,
                            sample_count=cp.sample_count,
                        )

                # Update overall pace
                all_paces = [c.avg_base_pace for c in sp.compound_profiles.values()]
                sp.overall_base_pace = round(sum(all_paces) / len(all_paces), 3) if all_paces else 90.0
            else:
                # New driver — create from track profile
                season.driver_profiles[drv_num] = SeasonDriverProfile(
                    driver_number=drv_num,
                    name=track_prof.name,
                    compound_profiles={
                        k: DriverCompoundProfile(
                            compound=v.compound,
                            avg_deg_per_lap=v.avg_deg_per_lap,
                            avg_base_pace=v.avg_base_pace,
                            sample_count=v.sample_count,
                        )
                        for k, v in track_prof.compound_profiles.items()
                    },
                    overall_base_pace=track_prof.overall_base_pace,
                    circuits_count=1,
                )

        season.circuits_analyzed.append(circuit_key)
        self.save(season)
        return season

    def get_driver_priors(
        self,
        year: int,
        driver_number: int,
        compound: str,
    ) -> tuple[float | None, float | None]:
        """
        Get cross-session learned priors for a driver/compound.

        Returns:
            Tuple of (expected_base_pace, expected_deg_slope) or (None, None)
            if no historical data.
        """
        season = self.load(year)
        profile = season.driver_profiles.get(driver_number)
        if profile is None:
            return None, None

        cp = profile.compound_profiles.get(compound.upper())
        if cp is None:
            # Try falling back to overall pace with generic deg
            return profile.overall_base_pace, None

        return cp.avg_base_pace, cp.avg_deg_per_lap
