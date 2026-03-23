"""
Simulation Service - Race replay simulation engine.

This module provides the core simulation functionality for replaying
F1 race sessions with real telemetry data from FastF1.

Architecture:
    - Decoupled from FastAPI for testability
    - Protocol-based interfaces for dependency injection
    - Async-first design for non-blocking I/O

Example:
    >>> service = SimulationService(app_state, connection_manager)
    >>> await service.start(2023, 1)  # Start Bahrain 2023
    >>> await service.stop()

Note:
    This service requires FastF1 cached data for optimal performance.
    First-time session loads may take several minutes.
"""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np
import pandas as pd

from rsw.config.constants import (
    DEFAULT_BASE_PACE_SECONDS,
    DEFAULT_PIT_LOSS_SECONDS,
    DEFAULT_TOTAL_LAPS,
    FRAME_INTERVAL_SECONDS,
    LOW_CONFIDENCE_PHYSICS_ONLY,
    MEDIUM_CONFIDENCE_DEFAULT,
)
from rsw.ingest.base import UpdateBatch
from rsw.logging_config import get_logger
from rsw.models.physics.track_characteristics import TrackCharacteristics, TrackLearner
from rsw.state import RaceState

if TYPE_CHECKING:
    from rsw.state.schemas import DriverState

# Module logger
logger = get_logger(__name__)


class IConnectionManager(Protocol):
    """
    Protocol for WebSocket connection management.

    Enables loose coupling between simulation and transport layer.
    """

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        ...


class IAppState(Protocol):
    """
    Protocol for application state container.

    Defines the minimal interface required by the simulation service.
    """

    store: Any  # RaceStateStore — typed as Any to avoid circular import
    speed_multiplier: float
    all_driver_telemetry: dict[str, dict[str, Any]]


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize data for JSON serialization.

    Replaces NaN and Infinity values with None to prevent
    JSON serialization errors. Also converts numpy types to native.

    Args:
        obj: Any Python object to sanitize

    Returns:
        Sanitized object safe for JSON serialization
    """
    if isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (int, np.integer)) and not isinstance(obj, bool):  # bool is int instance
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    return obj


class SimulationService:
    """
    Race simulation engine with real telemetry replay.

    Manages the complete lifecycle of a race simulation including:
    - Loading session data from FastF1
    - Processing lap-by-lap telemetry
    - Real-time strategy recommendations
    - Broadcasting state updates to clients

    Attributes:
        state: Application state container
        connection_manager: WebSocket broadcast interface
        strategy_service: Strategy calculation engine
        is_running: Whether simulation is currently active

    Thread Safety:
        This service is designed for single-threaded async operation.
        Do not share instances across event loops.
    """

    def __init__(
        self,
        state: IAppState,
        connection_manager: IConnectionManager,
    ) -> None:
        """
        Initialize the simulation service.

        Args:
            state: Application state container
            connection_manager: WebSocket connection manager for broadcasts
        """
        self.state = state
        self.connection_manager = connection_manager
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._replay_data: dict[str, Any] = {}
        self._lap_gaps: dict[int, dict[int, float]] = {}
        self._lap_positions: dict[int, dict[int, int]] = {}
        self._session_base_pace: float = DEFAULT_BASE_PACE_SECONDS

        # Initialize strategy service
        self._strategy_service = self._create_strategy_service()

        # Initialize degradation models
        from rsw.models.degradation.online_model import ModelManager

        self.model_manager = ModelManager()

        # Initialize Physics Models
        from rsw.models.physics.fuel_model import FuelModel
        from rsw.models.physics.track_model import TrackModel
        from rsw.models.physics.traffic_model import DirtyAirModel
        from rsw.models.physics.tyre_model import TyreModel

        self.physics_engine: dict[str, Any] = {
            "tyre": TyreModel,  # Factory
            "fuel": FuelModel(),
            "track": TrackModel(),
            "traffic": DirtyAirModel(),
        }

        # Track characteristics learner — learns from real FastF1 data
        self._track_learner = TrackLearner()
        self._track_characteristics: TrackCharacteristics | None = None

        # Season learner — aggregates driver profiles across circuits
        from rsw.models.physics.season_learner import SeasonLearner

        self._season_learner = SeasonLearner()

        # Resolved priors and optimizer (populated after track learning)
        self._resolved_priors: dict = {}
        self._track_pit_loss: float = DEFAULT_PIT_LOSS_SECONDS
        self._optimizer: Any = None

    def _create_strategy_service(self) -> Any:
        """Create and return a StrategyService instance."""
        try:
            from rsw.config.schemas import StrategyConfig
            from rsw.services.strategy_service import StrategyService

            # Use default strategy config
            config = StrategyConfig()
            return StrategyService(config)
        except Exception as e:
            logger.warning("strategy_service_init_failed", error=str(e))
            return None

    @property
    def is_running(self) -> bool:
        """Check if simulation is currently active."""
        return self._running

    async def start(self, year: int, round_number: int) -> None:
        """
        Start simulation for a specific race session.

        Stops any existing simulation before starting the new one.
        The simulation runs in a background task until stopped.

        Args:
            year: Season year (e.g., 2023)
            round_number: Round number in the championship

        Raises:
            ValueError: If year or round_number is invalid
        """
        await self.stop()

        logger.info(
            "simulation_starting",
            year=year,
            round=round_number,
        )

        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(year, round_number),
            name=f"simulation_{year}_r{round_number}",
        )

    async def stop(self) -> None:
        """
        Stop the current simulation gracefully.

        Cancels the background task and waits for cleanup.
        Safe to call even if no simulation is running.
        """
        self._running = False

        if self._task is not None:
            logger.info("simulation_stopping")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("simulation_stopped")

    async def set_speed(self, speed: float) -> None:
        """
        Set simulation playback speed.

        Args:
            speed: Playback multiplier (1.0 = real-time, 10.0 = 10x)

        Note:
            Speed changes take effect immediately without restart.
        """
        self.state.speed_multiplier = speed

    async def _run_loop(self, year: int, round_number: int) -> None:
        """
        Main simulation loop - processes laps until stopped.

        Args:
            year: Season year
            round_number: Round number
        """
        try:
            await self._load_data(year, round_number)

            state = self.state.store.get()
            max_lap = state.total_laps or DEFAULT_TOTAL_LAPS

            for current_lap in range(1, max_lap + 1):
                if not self._running:
                    break
                await self._process_lap(current_lap)

            logger.info("simulation_completed", total_laps=max_lap)

        except asyncio.CancelledError:
            logger.debug("simulation_cancelled")
        except Exception as e:
            logger.exception("simulation_error", error=str(e))

    async def _load_data(self, year: int, round_number: int) -> None:
        """
        Load all session data from FastF1.

        Args:
            year: Season year
            round_number: Round number

        Raises:
            RuntimeError: If session data cannot be loaded
        """
        logger.info("data_loading", year=year, round=round_number)

        try:
            from rsw.ingest.fastf1_service import (
                extract_race_data,
                get_or_load_session,
                get_track_geometry,
                get_weather_data,
            )

            session = await get_or_load_session(year, round_number, "R")

            track_geometry = await get_track_geometry(session)
            logger.debug("geometry_loaded", points=track_geometry.get("total_points", 0))

            self.state.all_driver_telemetry = await self._fetch_telemetry(session)
            logger.debug("telemetry_loaded", driver_count=len(self.state.all_driver_telemetry))

            self._lap_gaps = self._extract_lap_gaps(session)
            logger.debug("gaps_extracted", lap_count=len(self._lap_gaps))

            drivers, all_laps, all_stints, all_pits, all_race_control = extract_race_data(session)
            logger.debug("race_data_extracted", driver_count=len(drivers))

            session_key = int(f"{year}{round_number:02d}9999")
            meeting_key = getattr(session, "meeting_key", 0)
            session_name = getattr(session, "name", f"{year} Round {round_number}")

            # Track info from session event metadata
            event = getattr(session, "event", None)
            track_name = getattr(event, "Location", "") or session_name
            country = getattr(event, "Country", "")

            weather_data = await get_weather_data(session)
            current_weather = weather_data[0] if weather_data else self._default_weather()

            # Calibrate base pace from real lap data (replaces hardcoded 90.0)
            self._session_base_pace = self._calibrate_base_pace(all_laps)
            logger.info("base_pace_calibrated", base_pace=round(self._session_base_pace, 3))

            # Learn track characteristics from real race data
            try:
                circuit_key = (
                    getattr(event, "Location", "unknown").lower().replace(" ", "_")
                )
                circuit_name = getattr(event, "OfficialName", "") or track_name
                session_id = f"{year}_R{round_number}"

                # Convert Pydantic models to dicts for TrackLearner
                pit_dicts = [{"driver_number": p.driver_number, "lap_number": p.lap_number, "pit_duration": p.pit_duration} for p in all_pits]
                lap_dicts = [{"driver_number": l.driver_number, "lap_number": l.lap_number, "lap_duration": l.lap_duration, "is_pit_out_lap": l.is_pit_out_lap} for l in all_laps]
                stint_dicts = [{"driver_number": s.driver_number, "stint_number": s.stint_number, "compound": s.compound, "lap_start": s.lap_start, "lap_end": s.lap_end} for s in all_stints]

                position_dicts = [
                    {"driver_number": drv_num, "position": pos, "lap_number": lap_num}
                    for lap_num, pos_map in self._lap_positions.items()
                    for drv_num, pos in pos_map.items()
                ]

                total_race_laps = max(l.lap_number for l in all_laps) if all_laps else DEFAULT_TOTAL_LAPS

                self._track_characteristics = self._track_learner.learn_from_session(
                    circuit_key=circuit_key,
                    circuit_name=circuit_name,
                    session_id=session_id,
                    pit_data=pit_dicts,
                    lap_data=lap_dicts,
                    position_data=position_dicts,
                    stint_data=stint_dicts,
                    total_laps=total_race_laps,
                )
                logger.info(
                    "track_learned",
                    circuit=circuit_key,
                    pit_loss=round(self._track_characteristics.actual_pit_loss_mean, 2),
                    compounds=list(self._track_characteristics.compound_degradation.keys()),
                )

                # Update season-level driver profiles
                self._season_learner.update_from_track(year, self._track_characteristics)
                logger.info("season_profiles_updated", year=year, circuit=circuit_key)

                # Resolve track-learned priors for all compounds
                from rsw.models.degradation.track_priors import resolve_all_compounds, resolve_pit_loss

                self._resolved_priors = resolve_all_compounds(
                    track_chars=self._track_characteristics,
                    season_learner=self._season_learner,
                )
                self._track_pit_loss = resolve_pit_loss(self._track_characteristics)

                # Create multi-stop optimizer with track-specific params
                from rsw.strategy.multi_stop_optimizer import MultiStopOptimizer

                self._optimizer = MultiStopOptimizer(
                    pit_loss=self._track_pit_loss,
                    total_laps=total_race_laps,
                )

                logger.info(
                    "track_priors_resolved",
                    pit_loss=round(self._track_pit_loss, 2),
                    sources={c: p.source for c, p in self._resolved_priors.items()},
                )
            except Exception as e:
                logger.warning("track_learning_failed", error=str(e))
                self._track_characteristics = None

            # Reset degradation models — clears stale data from previous session
            self.model_manager.reset()

            await self.state.store.reset(
                RaceState(
                    session_key=session_key,
                    meeting_key=meeting_key,
                    session_name=session_name,
                    session_type="Race",
                    track_name=track_name,
                    country=country,
                    drivers={d.driver_number: d for d in drivers},
                    total_laps=max(l.lap_number for l in all_laps) if all_laps else DEFAULT_TOTAL_LAPS,
                    track_config=track_geometry,
                    weather=current_weather,
                )
            )

            self._replay_data = {
                "laps": all_laps,
                "stints": all_stints,
                "pits": all_pits,
                "race_control": all_race_control,
            }

            await self.connection_manager.broadcast(
                {
                    "type": "state_update",
                    "data": self.state.store.to_dict(),
                }
            )

            logger.info("data_loaded", session=session_name)

        except Exception as e:
            logger.exception("data_load_error", error=str(e))
            raise RuntimeError(f"Failed to load session data: {e}") from e

    @staticmethod
    def _default_weather() -> dict[str, Any]:
        """Return default weather data when real data unavailable."""
        return {
            "track_temp": 30.0,
            "air_temp": 25.0,
            "humidity": 50.0,
            "wind_speed": 5.0,
            "wind_direction": "N",
            "rainfall": 0.0,
            "is_raining": False,
        }

    async def _fetch_telemetry(self, session: Any) -> dict[str, Any]:
        """
        Fetch telemetry data from FastF1 session.

        Runs in thread executor to avoid blocking the event loop
        during heavy pandas operations.

        Args:
            session: FastF1 session object

        Returns:
            Dict mapping driver code to telemetry data
        """

        def _load() -> dict[str, Any]:
            data: dict[str, Any] = {}
            drivers_list = list(session.drivers) if hasattr(session, "drivers") else []

            # Check if laps are available
            if not hasattr(session, "laps"):
                return data

            try:
                for driver in drivers_list:
                    try:
                        laps = session.laps.pick_drivers(driver)
                        if laps.empty:
                            continue

                        driver_info = session.get_driver(driver)
                        code = driver_info.get("Abbreviation", str(driver))

                        lap = laps.pick_fastest()
                        if lap is None or (hasattr(lap, "empty") and lap.empty):
                            lap = laps.iloc[0]

                        telemetry = lap.get_telemetry()
                        if telemetry is not None and not telemetry.empty:
                            data[code] = {
                                "telemetry": telemetry,
                                "driver_number": int(driver),
                            }
                    except Exception as e:
                        logger.debug("telemetry_skip_driver", driver=driver, error=str(e))
                        continue
            except Exception as e:
                logger.warning("telemetry_load_failed", error=str(e))

            return data

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _load)

    def _extract_lap_gaps(self, session: Any) -> dict[int, dict[int, float]]:
        """
        Extract lap-by-lap gap and position data from session.

        Args:
            session: FastF1 session object

        Returns:
            Nested dict: {lap_number: {driver_number: gap_seconds}}
            Also populates self._lap_positions: {lap_number: {driver_number: position}}
        """
        lap_gaps: dict[int, dict[int, float]] = {}
        self._lap_positions = {}

        try:
            if not hasattr(session, "laps"):
                return lap_gaps

            laps_df = session.laps
            if laps_df.empty:
                return lap_gaps

            has_position_col = "Position" in laps_df.columns

            for lap_num in laps_df["LapNumber"].unique():
                lap_data = laps_df[laps_df["LapNumber"] == lap_num].copy()
                lap_data = lap_data.sort_values("Position")

                if lap_data.empty:
                    continue

                leader_time = lap_data.iloc[0]["Time"]
                if pd.isna(leader_time):
                    continue

                # Vectorized gap calculation
                driver_nums = lap_data["DriverNumber"].astype(int)
                times = lap_data["Time"]

                has_time = times.notna()
                time_gaps = pd.Series(0.0, index=lap_data.index)

                if has_time.any():
                    time_gaps[has_time] = (times[has_time] - leader_time).dt.total_seconds().clip(lower=0)

                if (~has_time).any():
                    positions = lap_data.loc[~has_time, "Position"]
                    time_gaps[~has_time] = positions.apply(
                        lambda pos: float((pos - 1) * 1.0) if pd.notna(pos) else 0.0
                    )

                gaps_for_lap = dict(zip(driver_nums, time_gaps))

                # Vectorized position extraction
                positions_for_lap: dict[int, int] = {}
                if has_position_col:
                    pos_col = lap_data["Position"]
                    valid_pos = pos_col.notna()
                    if valid_pos.any():
                        positions_for_lap = dict(zip(
                            driver_nums[valid_pos],
                            pos_col[valid_pos].astype(int),
                        ))

                lap_gaps[int(lap_num)] = gaps_for_lap
                self._lap_positions[int(lap_num)] = positions_for_lap

        except Exception as e:
            logger.warning("gap_extraction_failed", error=str(e))

        return lap_gaps

    async def _process_lap(self, current_lap: int) -> None:
        """
        Process a single lap of the simulation.

        Updates driver positions, telemetry, strategy recommendations,
        and broadcasts state to connected clients.

        Args:
            current_lap: Current lap number being simulated
        """
        all_laps = self._replay_data.get("laps", [])
        laps_this_lap = [lap for lap in all_laps if lap.lap_number == current_lap]

        avg_lap_time = self._get_average_lap_time(laps_this_lap)

        lap_batch = UpdateBatch(
            session_key=self.state.store.get().session_key,
            timestamp=datetime.now(UTC),
            current_lap=current_lap,
            laps=laps_this_lap,
            stints=self._get_active_stints(current_lap),
            pits=self._get_lap_pits(current_lap),
            race_control=self._get_recent_messages(current_lap),
        )
        await self.state.store.apply(lap_batch)

        # Run degradation + strategy updates concurrently with animation
        # to avoid blocking the 50fps render loop.
        async def _background_model_updates() -> None:
            try:
                await self._update_degradation(current_lap)
                # Only run strategy metrics every other lap to reduce CPU load
                if current_lap % 2 == 0 or current_lap <= 5:
                    await self._update_strategy_metrics(current_lap)
            except Exception as e:
                logger.warning("background_update_error", lap=current_lap, error=str(e))

        update_task = asyncio.create_task(_background_model_updates())

        await self._animate_lap(current_lap, avg_lap_time)

        # Ensure updates are done before next lap
        if not update_task.done():
            await update_task

    async def _update_degradation(self, current_lap: int) -> None:
        """
        Update tyre degradation models for all drivers.

        Args:
            current_lap: Current lap number
        """
        race_state = self.state.store.get()
        drivers = race_state.drivers

        if not drivers:
            return

        updated_drivers: dict[int, Any] = {}
        updates_count = 0

        for driver_num, driver in drivers.items():
            if driver.position is None or driver.position == 0:
                updated_drivers[driver_num] = driver
                continue

            # Seed model's base pace from calibrated session data on first encounter
            model = self.model_manager.get_or_create(driver.driver_number)
            if model.estimated_base_pace is None:
                model.estimated_base_pace = self._session_base_pace

            # Enable neural blending for nonlinear cliff prediction
            if model._neural_model is None:
                track_temp = race_state.weather.get("track_temp", 30.0) if race_state.weather else 30.0
                model.set_session_context(
                    track_temp=track_temp,
                    total_laps=race_state.total_laps or DEFAULT_TOTAL_LAPS,
                    session_avg_pace=self._session_base_pace,
                )

            # Get latest lap time if available
            last_lap_time = driver.last_lap_time
            compound = driver.compound or "MEDIUM"
            if last_lap_time and last_lap_time > 0:
                # Resolve season/track priors for this driver's compound
                season_priors = self._season_learner.get_driver_priors(
                    datetime.now(UTC).year, driver.driver_number, compound,
                )
                tp = self._resolved_priors.get(compound)

                # Update model (fuel-corrected: race_lap subtracted inside)
                self.model_manager.update_driver(
                    driver_number=driver.driver_number,
                    lap_in_stint=driver.lap_in_stint,
                    lap_time=last_lap_time,
                    stint_number=driver.stint_number,
                    compound=compound,
                    is_valid=True,  # Simplified validation
                    race_lap=current_lap,
                    season_priors=season_priors,
                    track_priors=tp,
                )

            # Get predictions from Online Model (RLS)
            model = self.model_manager.models.get(driver.driver_number)  # type: ignore[assignment]

            # Physics-based sanity check / Future prediction
            physics_pace = self._calculate_physics_pace(driver, current_lap)

            if model:
                deg_slope = model.get_deg_slope()
                cliff_risk = model.get_cliff_risk()
                prediction = model.get_prediction(k=5)

                # Verify RLS against Physics (Hybrid Approach)
                # If RLS has few samples, weight physics higher?
                # For now, we trust the live data (RLS) for current state,
                # but could use physics for long-term projection.

                updated_drivers[driver_num] = driver.model_copy(
                    update={
                        "deg_slope": deg_slope,
                        "cliff_risk": cliff_risk,
                        "predicted_pace": prediction.predicted_next_k
                        if prediction
                        else [physics_pace] * 5,
                        "model_confidence": prediction.model_confidence if prediction else MEDIUM_CONFIDENCE_DEFAULT,
                    }
                )
                updates_count += 1
            else:
                # No live model yet? Use Physics!
                updated_drivers[driver_num] = driver.model_copy(
                    update={
                        "predicted_pace": [physics_pace] * 5,
                        "model_confidence": LOW_CONFIDENCE_PHYSICS_ONLY,
                    }
                )
                updates_count += 1

        if updates_count > 0:
            new_state = race_state.model_copy(update={"drivers": updated_drivers})
            await self.state.store.reset(new_state)
            logger.debug("degradation_updated", lap=current_lap, updates=updates_count)

    def _calibrate_base_pace(self, all_laps: list) -> float:
        """
        Derive a realistic base lap time from the loaded session's lap data.

        Uses the 25th-percentile of valid clean racing laps (60-150s, non pit-out).
        This approximates typical fast-lap pace without being dragged up by
        SC/yellow-flag laps or pushed down by outliers.
        """
        valid_times = [
            lap.lap_duration
            for lap in all_laps
            if lap.lap_duration and 60.0 < lap.lap_duration < 150.0 and not lap.is_pit_out_lap
        ]
        if not valid_times:
            return DEFAULT_BASE_PACE_SECONDS
        valid_times.sort()
        # 25th percentile: represents clean competitive pace
        idx = max(0, len(valid_times) // 4)
        pace = valid_times[idx]
        return float(round(pace, 3))

    def _calculate_physics_pace(self, driver: DriverState, current_lap: int) -> float:
        """
        Calculate predicted lap time using physics models.
        Pace = Base + FuelPenalty + TyrePenalty - TrackEvolution + DirtyAir
        """
        # 1. Base Pace — calibrated from real session lap data (set in _load_session_data)
        base_pace = self._session_base_pace

        # 2. Fuel Penalty
        fuel_penalty = self.physics_engine["fuel"].get_fuel_penalty(current_lap)

        # 3. Tyre Penalty (Degradation + Compound Offset)
        tyre_model = self.physics_engine["tyre"](driver.compound or "MEDIUM")
        tyre_deg = tyre_model.get_tyre_penalty(driver.tyre_age)
        compound_offset = tyre_model.get_compound_pace_delta()

        # 4. Track Evolution (Gain)
        track_gain = self.physics_engine["track"].get_lap_evolution(current_lap)

        # 5. Traffic (Dirty Air)
        traffic_penalty = self.physics_engine["traffic"].get_pace_penalty(driver.gap_to_ahead)

        return base_pace + fuel_penalty + tyre_deg + compound_offset - track_gain + traffic_penalty  # type: ignore[no-any-return]

    async def _update_strategy_metrics(self, current_lap: int) -> None:
        """
        Update strategy recommendations for all drivers.

        Called once per lap to calculate pit windows, undercut threats,
        and overcut opportunities using the StrategyService.

        Args:
            current_lap: Current lap number
        """
        if self._strategy_service is None:
            return

        race_state = self.state.store.get()
        drivers = race_state.drivers

        if not drivers:
            return

        # Sort drivers for undercut/overcut analysis
        sorted_drivers = sorted(drivers.values(), key=lambda d: d.position if d.position else 999)

        updated_drivers: dict[int, Any] = {}

        for driver in sorted_drivers:
            if driver.position is None or driver.position == 0:
                updated_drivers[driver.driver_number] = driver
                continue

            try:
                # Look up real pit loss and cliff age from track-learned data
                pit_loss = (
                    self._track_characteristics.actual_pit_loss_mean
                    if self._track_characteristics and self._track_characteristics.pit_stop_count > 0
                    else DEFAULT_PIT_LOSS_SECONDS
                )
                compound = driver.compound or "MEDIUM"
                cliff_age = None
                if self._track_characteristics:
                    cd = self._track_characteristics.compound_degradation.get(compound.upper())
                    if cd:
                        cliff_age = cd.cliff_lap

                # Get strategy recommendation with real track data + optimizer
                recommendation = self._strategy_service.get_recommendation(
                    driver=driver,
                    race_state=race_state,
                    pit_loss=pit_loss,
                    cliff_age=cliff_age,
                    optimizer=self._optimizer,
                    track_priors=self._resolved_priors or None,
                )

                # Compute fuel laps remaining from physics model
                fuel_kg = self.physics_engine["fuel"].get_fuel_mass(driver.current_lap)
                burn_rate = self.physics_engine["fuel"].BURN_RATE_KG_PER_LAP
                fuel_laps = int(fuel_kg / burn_rate) if burn_rate > 0 else 0

                # Update driver with strategy data
                updated_drivers[driver.driver_number] = driver.model_copy(
                    update={
                        "pit_recommendation": recommendation.get("recommendation"),
                        "pit_reason": recommendation.get("reason"),
                        "pit_confidence": recommendation.get("confidence", 0.0),
                        "pit_window_min": recommendation.get("pit_window", {}).get("min", 0)
                        if recommendation.get("pit_window")
                        else driver.pit_window_min,
                        "pit_window_max": recommendation.get("pit_window", {}).get("max", 0)
                        if recommendation.get("pit_window")
                        else driver.pit_window_max,
                        "pit_window_ideal": recommendation.get("pit_window", {}).get("ideal", 0)
                        if recommendation.get("pit_window")
                        else driver.pit_window_ideal,
                        "undercut_threat": recommendation.get("undercut_threat", False),
                        "overcut_opportunity": recommendation.get("overcut_opportunity", False),
                        "fuel_remaining_kg": fuel_kg,
                        "fuel_laps_remaining": fuel_laps,
                    }
                )

            except Exception as e:
                logger.debug("strategy_update_error", driver=driver.driver_number, error=str(e))
                updated_drivers[driver.driver_number] = driver

        # Battle probability pass — uses predicted_pace + cliff_risk already on driver state
        from rsw.features.battle import compute_overtake_probability

        for driver_num, driver in updated_drivers.items():
            # Resolve effective gap: use stored interval if available, else compute from
            # gap_to_leader delta (simulation mode doesn't set gap_to_ahead directly)
            effective_gap = driver.gap_to_ahead
            if effective_gap is None:
                defender_for_gap = next(
                    (d for d in updated_drivers.values() if d.position == driver.position - 1),
                    None,
                )
                if (
                    defender_for_gap is not None
                    and driver.gap_to_leader is not None
                    and defender_for_gap.gap_to_leader is not None
                ):
                    effective_gap = driver.gap_to_leader - defender_for_gap.gap_to_leader

            if effective_gap is None or effective_gap > 1.5:
                if driver.overtake_probability is not None:
                    updated_drivers[driver_num] = driver.model_copy(
                        update={"overtake_probability": None, "battle_key_factor": None}
                    )
                continue

            defender = next(
                (d for d in updated_drivers.values() if d.position == driver.position - 1),
                None,
            )
            if defender is None:
                continue

            pace_att = driver.predicted_pace[0] if driver.predicted_pace else 0.0
            pace_def = defender.predicted_pace[0] if defender.predicted_pace else 0.0

            prob, key_factor = compute_overtake_probability(
                gap=effective_gap,
                drs_attacker=driver.drs,
                pace_next_attacker=pace_att,
                pace_next_defender=pace_def,
                cliff_risk_defender=defender.cliff_risk or 0.0,
                attacker_tyre_age=driver.tyre_age,
                defender_tyre_age=defender.tyre_age,
                attacker_compound=driver.compound or "HARD",
                defender_compound=defender.compound or "HARD",
            )
            updated_drivers[driver_num] = driver.model_copy(
                update={"overtake_probability": prob, "battle_key_factor": key_factor}
            )

        # Apply updates to state
        new_state = race_state.model_copy(update={"drivers": updated_drivers})
        await self.state.store.reset(new_state)

        logger.debug("strategy_metrics_updated", lap=current_lap, driver_count=len(updated_drivers))

    def _get_rivals(self, driver: Any, sorted_drivers: list[Any]) -> list[Any]:
        """
        Get rival drivers for undercut/overcut analysis.

        Returns drivers within 3 positions of the target driver.

        Args:
            driver: Target driver
            sorted_drivers: All drivers sorted by position

        Returns:
            List of rival drivers
        """
        if driver.position is None:
            return []

        return [
            d
            for d in sorted_drivers
            if d.driver_number != driver.driver_number
            and d.position is not None
            and abs(d.position - driver.position) <= 3
        ]

    def _get_average_lap_time(self, laps: list[Any]) -> float:
        """Get average lap time from lap data, fallback to calibrated session base pace."""
        for lap in laps:
            if lap.lap_duration and lap.lap_duration > 60:
                return float(lap.lap_duration)
        return self._session_base_pace

    def _get_active_stints(self, lap: int) -> list[Any]:
        """Get stints active during the given lap."""
        return [
            s
            for s in self._replay_data.get("stints", [])
            if s.lap_start <= lap and (s.lap_end is None or s.lap_end >= lap)
        ]

    def _get_lap_pits(self, lap: int) -> list[Any]:
        """Get pit stops occurring on the given lap."""
        return [p for p in self._replay_data.get("pits", []) if p.lap_number == lap]

    def _get_recent_messages(self, lap: int) -> list[Any] | None:
        """Get the 5 most recent race control messages."""
        messages = self._replay_data.get("race_control", [])
        if not messages:
            return None
        relevant = [m for m in messages if m.lap_number and m.lap_number <= lap]
        return relevant[-5:] if relevant else None

    async def _animate_lap(self, current_lap: int, avg_lap_time: float) -> None:
        """
        Animate driver positions through the lap.

        Updates at ~50 FPS with real telemetry data.

        Args:
            current_lap: Current lap number
            avg_lap_time: Expected lap duration in seconds
        """
        frame_interval = FRAME_INTERVAL_SECONDS
        last_frame = asyncio.get_event_loop().time()
        simulated_time = 0.0

        while self._running:
            current_time = asyncio.get_event_loop().time()
            delta = current_time - last_frame
            last_frame = current_time

            simulated_time += delta * self.state.speed_multiplier

            if simulated_time >= avg_lap_time:
                break

            # Read fresh state each frame so background RLS/strategy updates
            # (cliff_risk, deg_slope, etc.) are not overwritten by stale snapshots.
            current_drivers = self.state.store.get().drivers
            lap_fraction = simulated_time / avg_lap_time
            new_updates = self._calculate_driver_states(
                current_drivers, current_lap, lap_fraction, avg_lap_time
            )

            new_state = self.state.store.get().model_copy(
                update={
                    "drivers": new_updates,
                    "current_lap": current_lap,
                }
            )
            await self.state.store.reset(new_state)

            try:
                safe_data = sanitize_for_json(self.state.store.to_dict())
                await self.connection_manager.broadcast(
                    {
                        "type": "state_update",
                        "data": safe_data,
                    }
                )
            except Exception as e:
                logger.warning("broadcast_error", lap=current_lap, error=str(e))

            await asyncio.sleep(max(0.002, frame_interval - (asyncio.get_event_loop().time() - current_time)))

    def _calculate_driver_states(
        self,
        drivers: dict[int, Any],
        current_lap: int,
        lap_fraction: float,
        avg_lap_time: float,
    ) -> dict[int, Any]:
        """
        Calculate updated driver states based on telemetry.

        Args:
            drivers: Current driver states
            current_lap: Current lap number
            lap_fraction: Progress through current lap (0.0 - 1.0)
            avg_lap_time: Expected lap duration

        Returns:
            Updated driver states dict
        """
        sorted_drivers = sorted(drivers.values(), key=lambda d: d.position if d.position else 999)

        new_updates: dict[int, Any] = {}
        lap_gaps = self._lap_gaps.get(current_lap, {})
        lap_positions = self._lap_positions.get(current_lap, {})

        # Smooth fuel: interpolate from start-of-lap to end-of-lap value
        fuel_model = self.physics_engine["fuel"]
        fuel_start = fuel_model.get_fuel_mass(max(0, current_lap - 1))
        fuel_end = fuel_model.get_fuel_mass(current_lap)
        fuel_remaining = round(fuel_start - (fuel_start - fuel_end) * lap_fraction, 2)

        for driver in sorted_drivers:
            if driver.position == 0 or driver.position is None:
                new_updates[driver.driver_number] = driver.model_copy(
                    update={
                        "speed": 0,
                        "gear": 0,
                        "throttle": 0,
                        "brake": 0,
                        "drs": 0,
                        "rel_dist": None,
                        "x": None,
                        "y": None,
                        "gap_to_leader": None,
                    }
                )
                continue

            gap_to_leader = lap_gaps.get(driver.driver_number, 0.0)
            telemetry = self._get_driver_telemetry(
                driver, lap_fraction, gap_to_leader, avg_lap_time
            )

            # Real-time position from FastF1 lap data; fall back to stored position
            real_position = lap_positions.get(driver.driver_number, driver.position)

            new_updates[driver.driver_number] = driver.model_copy(
                update={
                    "speed": round(telemetry["speed"], 1),
                    "gear": telemetry["gear"],
                    "throttle": round(telemetry["throttle"], 1),
                    "brake": round(telemetry["brake"], 1),
                    "drs": telemetry["drs"],
                    "rel_dist": round(telemetry["rel_dist"], 4),
                    "x": round(telemetry["x"], 1) if telemetry["x"] is not None else None,
                    "y": round(telemetry["y"], 1) if telemetry["y"] is not None else None,
                    "gap_to_leader": round(gap_to_leader, 3),
                    "position": real_position,
                    "fuel_remaining_kg": fuel_remaining,
                }
            )

        return new_updates

    def _get_driver_telemetry(
        self,
        driver: Any,
        lap_fraction: float,
        gap_to_leader: float,
        avg_lap_time: float,
    ) -> dict[str, Any]:
        """
        Get telemetry data for a driver at current position.

        Args:
            driver: Driver state object
            lap_fraction: Progress through lap (0.0 - 1.0)
            gap_to_leader: Gap to leader in seconds
            avg_lap_time: Expected lap duration

        Returns:
            Dict with speed, gear, throttle, brake, drs, x, y, rel_dist
        """
        driver_code = driver.name_acronym or f"#{driver.driver_number}"
        telemetry_data = self.state.all_driver_telemetry.get(driver_code)

        default = {
            "speed": 0,
            "gear": 0,
            "throttle": 0,
            "brake": 0,
            "drs": 0,
            "x": None,
            "y": None,
            "rel_dist": 0.0,
        }

        if not telemetry_data or "telemetry" not in telemetry_data:
            return default

        t = telemetry_data["telemetry"]
        if hasattr(t, "empty") and t.empty:
            return default
        gap_fraction = (gap_to_leader / avg_lap_time) if avg_lap_time > 0 else 0
        driver_lap_fraction = (lap_fraction - gap_fraction) % 1.0

        idx = int(driver_lap_fraction * (len(t) - 1))
        idx = max(0, min(idx, len(t) - 1))

        drs_value = int(t["DRS"].iloc[idx]) if "DRS" in t.columns else 0
        drs = 1 if drs_value >= 10 else (8 if drs_value >= 8 else 0)

        return {
            "speed": float(t["Speed"].iloc[idx]),
            "gear": int(t["nGear"].iloc[idx]),
            "throttle": float(t["Throttle"].iloc[idx]),
            "brake": float(t["Brake"].iloc[idx]) * 100,
            "drs": drs,
            "x": float(t["X"].iloc[idx]),
            "y": float(t["Y"].iloc[idx]),
            "rel_dist": driver_lap_fraction,
        }
