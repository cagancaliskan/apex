"""
Track Characteristics Learning.

Learns track-specific data from FastF1 historical sessions:
- Actual pit loss times
- Overtaking success rates
- Tyre degradation rates per compound
- DRS effectiveness

Data is persisted to JSON for reuse across sessions.

Design: DRY - Uses shared extraction functions, single storage format.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CompoundDegradation:
    """Degradation data for a tyre compound."""

    compound: str
    avg_deg_per_lap: float  # Seconds lost per lap
    cliff_lap: int  # Typical cliff lap
    sample_count: int = 0  # Number of stints analyzed


@dataclass
class DriverCompoundProfile:
    """Per-compound degradation stats for a specific driver."""

    compound: str
    avg_deg_per_lap: float
    avg_base_pace: float
    sample_count: int = 0


@dataclass
class DriverProfile:
    """Cross-session performance profile for a single driver."""

    driver_number: int
    name: str = ""
    compound_profiles: dict[str, DriverCompoundProfile] = field(default_factory=dict)
    overall_base_pace: float = 90.0
    sessions_count: int = 0


@dataclass
class TrackCharacteristics:
    """
    Learned characteristics for a specific track.

    Aggregated from historical race data.
    """

    circuit_name: str
    circuit_key: str  # Short identifier (e.g., "bahrain")

    # Pit stop data
    actual_pit_loss_mean: float = 22.0  # Mean pit loss in seconds
    actual_pit_loss_std: float = 1.5  # Standard deviation
    pit_stop_count: int = 0  # Number of pit stops analyzed

    # Overtaking data
    overtaking_success_rate: float = 0.3  # Fraction of attempts that succeed
    position_changes_per_lap: float = 0.5  # Avg position changes per lap
    overtake_sample_count: int = 0

    # Per-compound degradation
    compound_degradation: dict[str, CompoundDegradation] = field(default_factory=dict)

    # DRS effectiveness
    drs_pass_rate: float = 0.4  # Success rate when DRS available
    drs_sample_count: int = 0

    # Per-driver cross-session profiles
    driver_profiles: dict[int, DriverProfile] = field(default_factory=dict)

    # Metadata
    last_updated: str = ""
    sessions_analyzed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrackCharacteristics":
        """Deserialize from dictionary."""
        # Handle compound_degradation separately
        compound_data = data.pop("compound_degradation", {})
        compound_deg = {
            k: CompoundDegradation(**v) for k, v in compound_data.items()
        }
        # Handle driver_profiles
        profile_data = data.pop("driver_profiles", {})
        driver_profiles = {}
        for drv_key, prof in profile_data.items():
            cp_data = prof.pop("compound_profiles", {})
            cp = {k: DriverCompoundProfile(**v) for k, v in cp_data.items()}
            driver_profiles[int(drv_key)] = DriverProfile(compound_profiles=cp, **prof)
        return cls(compound_degradation=compound_deg, driver_profiles=driver_profiles, **data)


class TrackLearner:
    """
    Learns track characteristics from FastF1 session data.

    Persists learned data to JSON files in the data directory.
    """

    def __init__(self, data_dir: Path | None = None):
        """
        Initialize the track learner.

        Args:
            data_dir: Directory to store learned data. Defaults to data/track_data/
        """
        if data_dir is None:
            # Default to project's data directory
            self.data_dir = Path(__file__).parent.parent.parent.parent / "data" / "track_data"
        else:
            self.data_dir = data_dir

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, TrackCharacteristics] = {}

    def _get_file_path(self, circuit_key: str) -> Path:
        """Get the file path for a circuit's data."""
        return self.data_dir / f"{circuit_key}.json"

    def load(self, circuit_key: str) -> TrackCharacteristics | None:
        """Load characteristics for a circuit."""
        # Check cache first
        if circuit_key in self._cache:
            return self._cache[circuit_key]

        file_path = self._get_file_path(circuit_key)
        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)
            characteristics = TrackCharacteristics.from_dict(data)
            self._cache[circuit_key] = characteristics
            return characteristics
        except (json.JSONDecodeError, TypeError, KeyError):
            return None

    def save(self, characteristics: TrackCharacteristics) -> None:
        """Save characteristics for a circuit."""
        file_path = self._get_file_path(characteristics.circuit_key)
        characteristics.last_updated = datetime.now().isoformat()

        with open(file_path, "w") as f:
            json.dump(characteristics.to_dict(), f, indent=2)

        self._cache[characteristics.circuit_key] = characteristics

    def extract_pit_loss(
        self,
        pit_data: list[dict[str, Any]],
        lap_data: list[dict[str, Any]],
    ) -> tuple[float, float, int]:
        """
        Extract actual pit loss from session data.

        Pit loss = (in-lap + out-lap) - (2 * average clean lap)

        Args:
            pit_data: List of pit stop records
            lap_data: List of lap records

        Returns:
            Tuple of (mean_pit_loss, std_pit_loss, sample_count)
        """
        if not pit_data or not lap_data:
            return 22.0, 1.5, 0  # Default values

        # Group laps by driver
        driver_laps: dict[int, list[dict]] = {}
        for lap in lap_data:
            driver = lap.get("driver_number")
            if driver:
                driver_laps.setdefault(driver, []).append(lap)

        pit_losses = []

        for pit in pit_data:
            driver = pit.get("driver_number")
            pit_lap = pit.get("lap_number")

            if not driver or not pit_lap or driver not in driver_laps:
                continue

            laps = driver_laps[driver]

            # Find in-lap, out-lap, and clean laps
            in_lap = next((l for l in laps if l.get("lap_number") == pit_lap), None)
            out_lap = next((l for l in laps if l.get("lap_number") == pit_lap + 1), None)

            if not in_lap or not out_lap:
                continue

            in_time = in_lap.get("lap_duration")
            out_time = out_lap.get("lap_duration")

            if not in_time or not out_time:
                continue

            # Calculate average clean lap for this driver
            clean_laps: list[float] = [
                l.get("lap_duration")  # type: ignore[misc]
                for l in laps
                if l.get("lap_duration")
                and not l.get("is_pit_out_lap")
                and l.get("lap_number") not in (pit_lap, pit_lap + 1)
            ]

            if len(clean_laps) < 3:
                continue

            avg_clean = sum(clean_laps) / len(clean_laps)

            # Pit loss = extra time spent vs two clean laps
            pit_loss = (in_time + out_time) - (2 * avg_clean)

            # Sanity check - pit loss should be positive and reasonable
            if 15.0 < pit_loss < 35.0:
                pit_losses.append(pit_loss)

        if not pit_losses:
            return 22.0, 1.5, 0

        import statistics

        mean = statistics.mean(pit_losses)
        std = statistics.stdev(pit_losses) if len(pit_losses) > 1 else 1.5

        return mean, std, len(pit_losses)

    def extract_overtaking_rate(
        self,
        position_data: list[dict[str, Any]],
        total_laps: int,
    ) -> tuple[float, int]:
        """
        Calculate overtaking rate from position changes.

        Args:
            position_data: List of position records sorted by timestamp
            total_laps: Total race laps

        Returns:
            Tuple of (position_changes_per_lap, sample_count)
        """
        if not position_data or total_laps == 0:
            return 0.5, 0

        # Count position changes per driver
        position_changes = 0
        prev_positions: dict[int, int] = {}

        for record in position_data:
            driver = record.get("driver_number")
            position = record.get("position")

            if not driver or not position:
                continue

            if driver in prev_positions and prev_positions[driver] != position:
                position_changes += 1

            prev_positions[driver] = position

        changes_per_lap = position_changes / total_laps if total_laps > 0 else 0

        return changes_per_lap, len(position_data)

    def extract_compound_degradation(
        self,
        stint_data: list[dict[str, Any]],
        lap_data: list[dict[str, Any]],
    ) -> dict[str, CompoundDegradation]:
        """
        Extract degradation rates per compound.

        Uses linear regression on stint lap times.

        Args:
            stint_data: List of stint records
            lap_data: List of lap records

        Returns:
            Dict mapping compound name to degradation data
        """
        if not stint_data or not lap_data:
            return {}

        # Group laps by stint
        lap_by_driver: dict[int, list[dict]] = {}
        for lap in lap_data:
            driver = lap.get("driver_number")
            if driver:
                lap_by_driver.setdefault(driver, []).append(lap)

        compound_stints: dict[str, list[tuple[list[float], int]]] = {}

        for stint in stint_data:
            driver = stint.get("driver_number")
            compound = stint.get("compound", "UNKNOWN")
            lap_start = stint.get("lap_start", 1)
            lap_end = stint.get("lap_end")

            if not driver or not lap_end or driver not in lap_by_driver:
                continue

            # Get lap times for this stint
            stint_laps = [
                l.get("lap_duration")
                for l in lap_by_driver[driver]
                if l.get("lap_duration")
                and lap_start <= l.get("lap_number", 0) <= lap_end
                and not l.get("is_pit_out_lap")
            ]

            if len(stint_laps) >= 5:  # Need at least 5 laps
                compound_stints.setdefault(compound, []).append(
                    (list(map(float, stint_laps)), lap_end - lap_start)  # type: ignore[arg-type]
                )

        # Calculate degradation for each compound
        result = {}
        for compound, stints in compound_stints.items():
            if not stints:
                continue

            deg_rates = []
            cliff_laps = []

            for lap_times, stint_length in stints:
                if len(lap_times) < 5:
                    continue

                # Simple linear regression for degradation
                n = len(lap_times)
                x_mean = (n - 1) / 2
                y_mean = sum(lap_times) / n

                numerator = sum((i - x_mean) * (t - y_mean) for i, t in enumerate(lap_times))
                denominator = sum((i - x_mean) ** 2 for i in range(n))

                if denominator > 0:
                    slope = numerator / denominator
                    if 0 < slope < 0.3:  # Reasonable degradation rate
                        deg_rates.append(slope)
                        cliff_laps.append(stint_length)

            if deg_rates:
                avg_deg = sum(deg_rates) / len(deg_rates)
                avg_cliff = int(sum(cliff_laps) / len(cliff_laps))

                result[compound] = CompoundDegradation(
                    compound=compound,
                    avg_deg_per_lap=round(avg_deg, 4),
                    cliff_lap=avg_cliff,
                    sample_count=len(deg_rates),
                )

        return result

    def extract_driver_profiles(
        self,
        stint_data: list[dict[str, Any]],
        lap_data: list[dict[str, Any]],
    ) -> dict[int, DriverProfile]:
        """
        Extract per-driver degradation profiles from session data.

        Computes per-driver, per-compound degradation rates and base pace
        for cross-session learning.
        """
        if not stint_data or not lap_data:
            return {}

        # Group laps by driver
        lap_by_driver: dict[int, list[dict]] = {}
        for lap in lap_data:
            driver = lap.get("driver_number")
            if driver:
                lap_by_driver.setdefault(driver, []).append(lap)

        profiles: dict[int, DriverProfile] = {}

        for stint in stint_data:
            driver = stint.get("driver_number")
            compound = stint.get("compound", "UNKNOWN")
            lap_start = stint.get("lap_start", 1)
            lap_end = stint.get("lap_end")

            if not driver or not lap_end or driver not in lap_by_driver:
                continue

            # Get clean lap times for this stint
            stint_laps: list[float] = [
                l.get("lap_duration")  # type: ignore[misc]
                for l in lap_by_driver[driver]
                if l.get("lap_duration")
                and lap_start <= l.get("lap_number", 0) <= lap_end
                and not l.get("is_pit_out_lap")
                and 60.0 < l.get("lap_duration", 0) < 150.0
            ]

            if len(stint_laps) < 5:
                continue

            # Linear regression for degradation
            n = len(stint_laps)
            x_mean = (n - 1) / 2
            y_mean = sum(stint_laps) / n
            numerator = sum((i - x_mean) * (t - y_mean) for i, t in enumerate(stint_laps))
            denominator = sum((i - x_mean) ** 2 for i in range(n))

            if denominator <= 0:
                continue
            slope = numerator / denominator
            if not (0 < slope < 0.3):
                continue

            base_pace = stint_laps[0]  # First clean lap as base

            # Create or update driver profile
            if driver not in profiles:
                profiles[driver] = DriverProfile(
                    driver_number=driver,
                    overall_base_pace=base_pace,
                    sessions_count=1,
                )

            prof = profiles[driver]
            if compound in prof.compound_profiles:
                old = prof.compound_profiles[compound]
                total = old.sample_count + 1
                prof.compound_profiles[compound] = DriverCompoundProfile(
                    compound=compound,
                    avg_deg_per_lap=round((old.avg_deg_per_lap * old.sample_count + slope) / total, 4),
                    avg_base_pace=round((old.avg_base_pace * old.sample_count + base_pace) / total, 3),
                    sample_count=total,
                )
            else:
                prof.compound_profiles[compound] = DriverCompoundProfile(
                    compound=compound,
                    avg_deg_per_lap=round(slope, 4),
                    avg_base_pace=round(base_pace, 3),
                    sample_count=1,
                )

            # Update overall base pace
            all_paces = [cp.avg_base_pace for cp in prof.compound_profiles.values()]
            prof.overall_base_pace = round(sum(all_paces) / len(all_paces), 3)

        return profiles

    def learn_from_session(
        self,
        circuit_key: str,
        circuit_name: str,
        session_id: str,
        pit_data: list[dict[str, Any]],
        lap_data: list[dict[str, Any]],
        position_data: list[dict[str, Any]],
        stint_data: list[dict[str, Any]],
        total_laps: int,
    ) -> TrackCharacteristics:
        """
        Learn characteristics from a session and merge with existing data.

        Args:
            circuit_key: Short circuit identifier
            circuit_name: Full circuit name
            session_id: Unique session identifier
            pit_data: Pit stop records
            lap_data: Lap records
            position_data: Position records
            stint_data: Stint records
            total_laps: Total race laps

        Returns:
            Updated TrackCharacteristics
        """
        # Load existing or create new
        existing = self.load(circuit_key)
        if existing is None:
            existing = TrackCharacteristics(
                circuit_name=circuit_name,
                circuit_key=circuit_key,
            )

        # Skip if already processed
        if session_id in existing.sessions_analyzed:
            return existing

        # Extract new data
        pit_mean, pit_std, pit_count = self.extract_pit_loss(pit_data, lap_data)
        overtake_rate, overtake_count = self.extract_overtaking_rate(position_data, total_laps)
        compound_deg = self.extract_compound_degradation(stint_data, lap_data)

        # Merge with existing (weighted average)
        if existing.pit_stop_count > 0 and pit_count > 0:
            total_pits = existing.pit_stop_count + pit_count
            existing.actual_pit_loss_mean = (
                existing.actual_pit_loss_mean * existing.pit_stop_count + pit_mean * pit_count
            ) / total_pits
            existing.actual_pit_loss_std = (pit_std + existing.actual_pit_loss_std) / 2
            existing.pit_stop_count = total_pits
        elif pit_count > 0:
            existing.actual_pit_loss_mean = pit_mean
            existing.actual_pit_loss_std = pit_std
            existing.pit_stop_count = pit_count

        # Merge overtaking data
        if existing.overtake_sample_count > 0 and overtake_count > 0:
            existing.position_changes_per_lap = (
                existing.position_changes_per_lap + overtake_rate
            ) / 2
            existing.overtake_sample_count += overtake_count
        elif overtake_count > 0:
            existing.position_changes_per_lap = overtake_rate
            existing.overtake_sample_count = overtake_count

        # Merge compound degradation
        for compound, deg in compound_deg.items():
            if compound in existing.compound_degradation:
                old = existing.compound_degradation[compound]
                total = old.sample_count + deg.sample_count
                existing.compound_degradation[compound] = CompoundDegradation(
                    compound=compound,
                    avg_deg_per_lap=(
                        old.avg_deg_per_lap * old.sample_count + deg.avg_deg_per_lap * deg.sample_count
                    )
                    / total,
                    cliff_lap=(old.cliff_lap + deg.cliff_lap) // 2,
                    sample_count=total,
                )
            else:
                existing.compound_degradation[compound] = deg

        # Extract and merge driver profiles
        driver_profiles = self.extract_driver_profiles(stint_data, lap_data)
        for drv_num, profile in driver_profiles.items():
            if drv_num in existing.driver_profiles:
                old_prof = existing.driver_profiles[drv_num]
                old_prof.sessions_count += 1
                # Merge compound profiles
                for comp, cp in profile.compound_profiles.items():
                    if comp in old_prof.compound_profiles:
                        old_cp = old_prof.compound_profiles[comp]
                        total = old_cp.sample_count + cp.sample_count
                        old_prof.compound_profiles[comp] = DriverCompoundProfile(
                            compound=comp,
                            avg_deg_per_lap=round(
                                (old_cp.avg_deg_per_lap * old_cp.sample_count
                                 + cp.avg_deg_per_lap * cp.sample_count) / total, 4),
                            avg_base_pace=round(
                                (old_cp.avg_base_pace * old_cp.sample_count
                                 + cp.avg_base_pace * cp.sample_count) / total, 3),
                            sample_count=total,
                        )
                    else:
                        old_prof.compound_profiles[comp] = cp
                # Update overall base pace
                all_paces = [c.avg_base_pace for c in old_prof.compound_profiles.values()]
                old_prof.overall_base_pace = round(sum(all_paces) / len(all_paces), 3)
            else:
                existing.driver_profiles[drv_num] = profile

        existing.sessions_analyzed.append(session_id)
        self.save(existing)

        return existing


def get_pit_loss_for_circuit(circuit_key: str, default: float = 22.0) -> float:
    """
    Get learned pit loss for a circuit.

    Falls back to default if no learned data available.
    """
    learner = TrackLearner()
    characteristics = learner.load(circuit_key)

    if characteristics and characteristics.pit_stop_count > 0:
        return characteristics.actual_pit_loss_mean

    return default


def get_compound_cliff_lap(
    circuit_key: str,
    compound: str,
    default: int = 25,
) -> int:
    """
    Get learned cliff lap for compound at circuit.

    Falls back to default if no learned data.
    """
    learner = TrackLearner()
    characteristics = learner.load(circuit_key)

    if characteristics and compound.upper() in characteristics.compound_degradation:
        return characteristics.compound_degradation[compound.upper()].cliff_lap

    return default
