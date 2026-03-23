"""
Live Race Service - Real-time F1 session tracking via OpenF1 API polling.

Polls OpenF1 at configurable intervals during live sessions, feeds data
through the existing state/strategy pipeline, and broadcasts updates
to connected WebSocket clients.

Architecture:
    - Reuses OpenF1Client.fetch_update_batch() for incremental data fetching
    - Reuses existing reducers (apply_update_batch) for state building
    - Reuses ModelManager + StrategyService for degradation/pit analysis
    - No animation loop: one state broadcast per poll cycle

Example:
    >>> service = LiveRaceService(app_state, conn_mgr, openf1_client, weather_client)
    >>> await service.start(session_key=9573)
    >>> # ... service polls every 5s until stopped or session ends
    >>> await service.stop()
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from rsw.config.constants import (
    DEFAULT_BASE_PACE_SECONDS,
    DEFAULT_PIT_LOSS_SECONDS,
    LOW_CONFIDENCE_PHYSICS_ONLY,
    MEDIUM_CONFIDENCE_DEFAULT,
)
from rsw.ingest.base import SessionInfo, UpdateBatch
from rsw.logging_config import get_logger
from rsw.runtime_config import get_config
from rsw.services.simulation_service import IAppState, IConnectionManager, sanitize_for_json

if TYPE_CHECKING:
    from rsw.ingest.openf1_client import OpenF1Client
    from rsw.ingest.weather_client import WeatherClient
    from rsw.strategy.multi_stop_optimizer import MultiStopOptimizer

logger = get_logger(__name__)


class LiveRaceService:
    """
    Real-time F1 session tracker via OpenF1 API polling.

    Polls the OpenF1 API at regular intervals, processes incoming data
    through degradation models and strategy engine, then broadcasts
    state updates to WebSocket clients.

    Attributes:
        is_running: Whether live tracking is currently active
        session_key: Currently tracked session key
    """

    def __init__(
        self,
        state: IAppState,
        connection_manager: IConnectionManager,
        openf1_client: OpenF1Client,
        weather_client: WeatherClient,
    ) -> None:
        self.state = state
        self.connection_manager = connection_manager
        self._client = openf1_client
        self._weather_client = weather_client

        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._session_key: int | None = None
        self._session_info: SessionInfo | None = None

        # Incremental fetch tracking
        self._last_lap: int = 0
        self._last_rc_count: int = 0

        # Polling config
        config = get_config()
        self._poll_interval: float = config.polling.live_race_interval
        self._weather_interval: float = config.polling.live_weather_interval
        self._max_errors: int = config.polling.live_max_consecutive_errors

        # Error tracking
        self._consecutive_errors: int = 0
        self._empty_polls: int = 0
        self._last_poll_time: float = 0.0
        self._last_weather_time: float = 0.0

        # Strategy and degradation
        self._strategy_service = self._create_strategy_service()
        self._model_manager = self._create_model_manager()
        self._session_base_pace: float = DEFAULT_BASE_PACE_SECONDS

        # Circuit key for weather lookups
        self._circuit_key: str | None = None

        # Track & season learning (adaptive priors)
        from rsw.models.degradation.track_priors import ResolvedPriors
        from rsw.models.physics.season_learner import SeasonLearner
        from rsw.models.physics.track_characteristics import TrackCharacteristics, TrackLearner

        self._track_learner = TrackLearner()
        self._season_learner = SeasonLearner()
        self._track_characteristics: TrackCharacteristics | None = None
        self._resolved_priors: dict[str, ResolvedPriors] = {}
        self._track_pit_loss: float = DEFAULT_PIT_LOSS_SECONDS
        self._optimizer: "MultiStopOptimizer | None" = None

    # =========================================================================
    # Public API
    # =========================================================================

    @property
    def is_running(self) -> bool:
        """Check if live tracking is active."""
        return self._running

    @property
    def session_key(self) -> int | None:
        """Currently tracked session key."""
        return self._session_key

    async def start(self, session_key: int) -> dict[str, Any]:
        """
        Start live tracking for a session.

        Fetches initial session info and drivers, initializes state,
        then spawns the background poll loop.

        Args:
            session_key: OpenF1 session key to track

        Returns:
            Session metadata dict
        """
        # Stop if already running
        if self._running:
            await self.stop()

        logger.info("live_starting", session_key=session_key)

        # Fetch session info
        self._session_info = await self._client.get_session(session_key)
        if not self._session_info:
            logger.warning("live_session_not_found", session_key=session_key)
            return {"status": "error", "detail": "Session not found"}

        self._session_key = session_key

        # Set poll interval based on session type
        config = get_config()
        if self._session_info.session_type == "Race":
            self._poll_interval = config.polling.live_race_interval
        else:
            self._poll_interval = config.polling.live_practice_interval

        # Derive circuit key for weather lookups
        self._circuit_key = self._session_info.circuit_short_name.lower().replace(" ", "_")

        # Load track-learned priors (adaptive pit loss, cliff ages, deg rates)
        self._load_track_priors()

        # Fetch initial drivers and build initial state
        initial_batch = await self._client.fetch_update_batch(
            session_key, include_drivers=True
        )
        await self.state.store.apply(initial_batch)

        # Calibrate base pace from initial lap data
        if initial_batch.laps:
            self._session_base_pace = self._calibrate_base_pace(initial_batch.laps)
            self._last_lap = max(lap.lap_number for lap in initial_batch.laps)

        # Reset tracking state
        self._consecutive_errors = 0
        self._empty_polls = 0
        self._last_weather_time = 0.0
        self._running = True

        # Spawn poll loop
        self._task = asyncio.create_task(self._poll_loop())

        # Broadcast initial state
        await self._broadcast_state()

        metadata = {
            "status": "started",
            "session_key": session_key,
            "session_name": self._session_info.session_name,
            "circuit": self._session_info.circuit_short_name,
            "country": self._session_info.country_name,
            "session_type": self._session_info.session_type,
        }
        logger.info("live_started", **metadata)
        return metadata

    async def stop(self) -> None:
        """Stop live tracking and clean up."""
        if not self._running:
            return

        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

        logger.info("live_stopped", session_key=self._session_key)

        # Broadcast stopped notification
        await self.connection_manager.broadcast(
            {"type": "live_stopped", "reason": "user_stopped"}
        )

        self._session_key = None
        self._session_info = None

    def get_status(self) -> dict[str, Any]:
        """Get current live tracking status."""
        race_state = self.state.store.get()
        return {
            "running": self._running,
            "session_key": self._session_key,
            "session_name": self._session_info.session_name if self._session_info else None,
            "circuit": self._session_info.circuit_short_name if self._session_info else None,
            "current_lap": race_state.current_lap if race_state else 0,
            "total_laps": race_state.total_laps if race_state else None,
            "poll_interval": self._poll_interval,
            "consecutive_errors": self._consecutive_errors,
            "last_poll_time": self._last_poll_time,
        }

    async def get_active_sessions(self) -> list[dict[str, Any]]:
        """
        Fetch sessions that may be currently active.

        Filters to the current year and returns sessions from today or recent days.
        """
        current_year = datetime.now(UTC).year
        try:
            sessions = await self._client.get_sessions(year=current_year)
        except Exception as e:
            logger.warning("live_session_fetch_failed", error=str(e))
            return []

        now = datetime.now(UTC)
        active = []
        for s in sessions:
            # Skip if ended more than 3 days ago
            if s.date_end and (now - s.date_end).total_seconds() > 3 * 86400:
                continue
            # Skip if starting more than 7 days in the future
            if s.date_start > now and (s.date_start - now).total_seconds() > 7 * 86400:
                continue
            # Skip if started more than 3 days ago with no end date
            if s.date_start <= now and not s.date_end and (now - s.date_start).total_seconds() > 3 * 86400:
                continue
            active.append({
                "session_key": s.session_key,
                "session_name": s.session_name,
                "session_type": s.session_type,
                "circuit": s.circuit_short_name,
                "country": s.country_name,
                "date_start": s.date_start.isoformat(),
            })

        return active

    # =========================================================================
    # Poll Loop
    # =========================================================================

    async def _poll_loop(self) -> None:
        """Main polling loop. Runs until stopped or session ends."""
        logger.info("live_poll_loop_started", interval=self._poll_interval)

        while self._running:
            try:
                had_new_data = await self._poll_cycle()

                if had_new_data:
                    self._consecutive_errors = 0
                    self._empty_polls = 0
                    # Restore normal interval if it was increased due to errors
                    config = get_config()
                    if self._session_info and self._session_info.session_type == "Race":
                        self._poll_interval = config.polling.live_race_interval
                    else:
                        self._poll_interval = config.polling.live_practice_interval
                else:
                    self._empty_polls += 1

                # Session end detection
                race_state = self.state.store.get()
                if (
                    self._empty_polls >= 10
                    and race_state.total_laps
                    and race_state.current_lap >= race_state.total_laps
                ):
                    logger.info("live_session_ended", session_key=self._session_key)
                    self._running = False
                    await self.connection_manager.broadcast(
                        {"type": "live_stopped", "reason": "session_ended"}
                    )
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._consecutive_errors += 1
                logger.warning(
                    "live_poll_error",
                    error=str(e),
                    consecutive_errors=self._consecutive_errors,
                )

                if self._consecutive_errors >= self._max_errors:
                    self._poll_interval = 30.0
                    logger.warning(
                        "live_degraded_mode",
                        new_interval=30.0,
                        reason="too_many_consecutive_errors",
                    )

            await asyncio.sleep(self._poll_interval)

        logger.info("live_poll_loop_ended")

    async def _poll_cycle(self) -> bool:
        """
        Execute one poll cycle: fetch data, update state, broadcast.

        Returns:
            True if new data was received
        """
        if not self._session_key:
            return False

        self._last_poll_time = time.time()

        # Fetch incremental data
        batch = await self._client.fetch_update_batch(
            self._session_key, since_lap=self._last_lap
        )

        # Check if we got new lap data
        has_new_laps = bool(batch.laps and len(batch.laps) > 0)

        if has_new_laps and batch.laps is not None:
            new_max_lap = max(lap.lap_number for lap in batch.laps)
            if new_max_lap > self._last_lap:
                self._last_lap = new_max_lap

                # Recalibrate base pace with new data
                self._session_base_pace = self._calibrate_base_pace(batch.laps)

        # Apply all data through reducers (positions, intervals, stints etc. update even without new laps)
        await self.state.store.apply(batch)

        # Run strategy update if we have new lap data
        if has_new_laps:
            current_lap = batch.current_lap or self._last_lap
            await self._run_strategy_update(current_lap)

        # Poll weather if interval elapsed
        now = time.time()
        if self._circuit_key and (now - self._last_weather_time) >= self._weather_interval:
            await self._poll_weather(self._circuit_key)
            self._last_weather_time = now

        # Broadcast state to all clients
        await self._broadcast_state()

        return has_new_laps

    # =========================================================================
    # Strategy & Degradation
    # =========================================================================

    async def _run_strategy_update(self, current_lap: int) -> None:
        """
        Update degradation models and strategy recommendations for all drivers.

        Adapted from SimulationService._update_degradation() and
        _update_strategy_metrics().
        """
        race_state = self.state.store.get()
        drivers = race_state.drivers

        if not drivers:
            return

        updated_drivers: dict[int, Any] = {}
        # Preserve degradation predictions so the battle pass can reuse them
        degradation_predictions: dict[int, Any] = {}

        for driver_num, driver in drivers.items():
            if driver.position is None or driver.position == 0:
                updated_drivers[driver_num] = driver
                continue

            # --- Degradation model update ---
            model = self._model_manager.get_or_create(driver.driver_number)
            if model.estimated_base_pace is None:
                model.estimated_base_pace = self._session_base_pace

            # Enable neural blending for nonlinear cliff prediction
            if model._neural_model is None:
                track_temp = race_state.weather.get("air_temp", 30.0) if race_state.weather else 30.0
                total_laps = race_state.total_laps or 57
                model.set_session_context(
                    track_temp=track_temp,
                    total_laps=total_laps,
                    session_avg_pace=self._session_base_pace,
                )

            last_lap_time = driver.last_lap_time
            compound = driver.compound or "MEDIUM"
            if last_lap_time and last_lap_time > 0:
                # Resolve priors for this driver+compound
                season_priors = self._season_learner.get_driver_priors(
                    datetime.now(UTC).year, driver.driver_number, compound,
                )
                tp = self._resolved_priors.get(compound)

                self._model_manager.update_driver(
                    driver_number=driver.driver_number,
                    lap_in_stint=driver.lap_in_stint,
                    lap_time=last_lap_time,
                    stint_number=driver.stint_number,
                    compound=compound,
                    is_valid=True,
                    race_lap=current_lap,
                    season_priors=season_priors,
                    track_priors=tp,
                )

            # Get RLS predictions
            rls_model = self._model_manager.models.get(driver.driver_number)
            deg_slope = driver.deg_slope
            cliff_risk = driver.cliff_risk
            predicted_pace = driver.predicted_pace
            model_confidence = driver.model_confidence

            if rls_model:
                deg_slope = rls_model.get_deg_slope()
                cliff_risk = rls_model.get_cliff_risk()
                prediction = rls_model.get_prediction(k=5)
                if prediction:
                    predicted_pace = prediction.predicted_next_k
                    model_confidence = prediction.model_confidence
                    degradation_predictions[driver_num] = prediction
                else:
                    model_confidence = MEDIUM_CONFIDENCE_DEFAULT
            else:
                model_confidence = LOW_CONFIDENCE_PHYSICS_ONLY

            # --- Strategy recommendation ---
            pit_recommendation = driver.pit_recommendation
            pit_reason = driver.pit_reason
            pit_confidence = driver.pit_confidence
            pit_window_min = driver.pit_window_min
            pit_window_max = driver.pit_window_max
            pit_window_ideal = driver.pit_window_ideal
            undercut_threat = driver.undercut_threat
            overcut_opportunity = driver.overcut_opportunity

            if self._strategy_service:
                try:
                    recommendation = self._strategy_service.get_recommendation(
                        driver=driver,
                        race_state=race_state,
                        pit_loss=self._track_pit_loss,
                        optimizer=self._optimizer,
                        track_priors=self._resolved_priors or None,
                    )
                    pit_recommendation = recommendation.get("recommendation")
                    pit_reason = recommendation.get("reason")
                    pit_confidence = recommendation.get("confidence", 0.0)
                    undercut_threat = recommendation.get("undercut_threat", False)
                    overcut_opportunity = recommendation.get("overcut_opportunity", False)

                    pw = recommendation.get("pit_window")
                    if pw:
                        pit_window_min = pw.get("min", 0)
                        pit_window_max = pw.get("max", 0)
                        pit_window_ideal = pw.get("ideal", 0)
                except Exception as e:
                    logger.debug(
                        "live_strategy_error",
                        driver=driver.driver_number,
                        error=str(e),
                    )

            updated_drivers[driver_num] = driver.model_copy(
                update={
                    "deg_slope": deg_slope,
                    "cliff_risk": cliff_risk,
                    "predicted_pace": predicted_pace,
                    "model_confidence": model_confidence,
                    "pit_recommendation": pit_recommendation,
                    "pit_reason": pit_reason,
                    "pit_confidence": pit_confidence,
                    "pit_window_min": pit_window_min,
                    "pit_window_max": pit_window_max,
                    "pit_window_ideal": pit_window_ideal,
                    "undercut_threat": undercut_threat,
                    "overcut_opportunity": overcut_opportunity,
                }
            )

        # --- Battle probability second pass ---
        # Runs after all degradation predictions are collected so both
        # attacker and defender predictions are available.
        from rsw.features.battle import compute_overtake_probability

        for driver_num, driver in updated_drivers.items():
            # Prefer stored gap_to_ahead (interval); fall back to gap_to_leader delta
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

            pred_att = degradation_predictions.get(driver_num)
            pred_def = degradation_predictions.get(defender.driver_number)
            pace_att = (pred_att.predicted_next_k[0] if pred_att and pred_att.predicted_next_k else 0.0)
            pace_def = (pred_def.predicted_next_k[0] if pred_def and pred_def.predicted_next_k else 0.0)

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

        logger.debug("live_strategy_updated", lap=current_lap, drivers=len(updated_drivers))

    # =========================================================================
    # Weather
    # =========================================================================

    async def _poll_weather(self, circuit_key: str) -> None:
        """Fetch current weather and update race state."""
        try:
            current = await self._weather_client.get_current(circuit_key)
            if not current:
                return

            forecast = await self._weather_client.get_forecast(circuit_key, hours=2)

            race_state = self.state.store.get()
            weather_update = {
                "air_temp": current.temperature,
                "humidity": current.humidity,
                "wind_speed": current.wind_speed,
                "rainfall": current.precipitation,
                "is_raining": current.is_wet,
                "rain_risk": current.rain_risk,
            }

            if forecast:
                weather_update["rain_probability"] = forecast.max_rain_probability
                weather_update["rain_expected"] = forecast.is_rain_expected

            new_state = race_state.model_copy(update={"weather": weather_update})
            await self.state.store.reset(new_state)

            logger.debug("live_weather_updated", circuit=circuit_key)

        except Exception as e:
            logger.warning("live_weather_error", circuit=circuit_key, error=str(e))

    # =========================================================================
    # Helpers
    # =========================================================================

    async def _broadcast_state(self) -> None:
        """Broadcast current race state to all WebSocket clients."""
        safe_data = sanitize_for_json(self.state.store.to_dict())
        await self.connection_manager.broadcast({
            "type": "state_update",
            "data": safe_data,
        })

    def _calibrate_base_pace(self, laps: list) -> float:
        """Derive base lap time from 25th percentile of clean laps."""
        valid_times = [
            lap.lap_duration
            for lap in laps
            if lap.lap_duration and 60.0 < lap.lap_duration < 150.0 and not lap.is_pit_out_lap
        ]
        if not valid_times:
            return self._session_base_pace
        valid_times.sort()
        idx = max(0, len(valid_times) // 4)
        return float(round(valid_times[idx], 3))

    def _create_strategy_service(self) -> Any:
        """Create a StrategyService instance."""
        try:
            from rsw.config.schemas import StrategyConfig
            from rsw.services.strategy_service import StrategyService

            return StrategyService(StrategyConfig())
        except Exception as e:
            logger.warning("live_strategy_service_init_failed", error=str(e))
            return None

    def _create_model_manager(self) -> Any:
        """Create a ModelManager for degradation tracking."""
        from rsw.models.degradation.online_model import ModelManager

        return ModelManager()

    def _load_track_priors(self) -> None:
        """Load track-learned priors and create the multi-stop optimizer."""
        if not self._circuit_key:
            return

        try:
            self._track_characteristics = self._track_learner.load(self._circuit_key)

            if self._track_characteristics:
                from rsw.models.degradation.track_priors import resolve_all_compounds, resolve_pit_loss

                self._resolved_priors = resolve_all_compounds(
                    track_chars=self._track_characteristics,
                    season_learner=self._season_learner,
                )
                self._track_pit_loss = resolve_pit_loss(self._track_characteristics)

                logger.info(
                    "live_track_priors_loaded",
                    circuit=self._circuit_key,
                    pit_loss=self._track_pit_loss,
                    compounds_learned=list(self._track_characteristics.compound_degradation.keys()),
                )

            # Create multi-stop optimizer with track-specific params
            from rsw.strategy.multi_stop_optimizer import MultiStopOptimizer

            race_state = self.state.store.get()
            total_laps = race_state.total_laps or 57
            self._optimizer = MultiStopOptimizer(
                pit_loss=self._track_pit_loss,
                total_laps=total_laps,
            )

        except Exception as e:
            logger.warning("live_track_priors_failed", error=str(e))
