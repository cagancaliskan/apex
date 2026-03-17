"""
Competitor AI Strategy Engine.

Simulates rational decision making for rival drivers.
Instead of random pit stops, rivals will:
1. Pit when tyres are dead (Cliff).
2. Cover undercuts if they are threatened.
3. Gamble on Safety Cars.
4. Use team profiles for strategy tendencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rsw.strategy.team_profiles import get_team_profile, will_react_to_safety_car


@dataclass
class CompetitorState:
    """State snapshot for a competitor driver."""

    driver_number: int
    team_name: str
    current_lap: int
    tyre_age: int
    compound: str
    position: int
    gap_to_behind: float | None = None


@dataclass
class StrategyDecision:
    should_pit: bool
    compound: str
    reason: str
    predicted_pit_lap: int | None = None


class CompetitorAI:
    """Enhanced competitor strategy engine with team profile integration."""

    def decide_strategy(
        self,
        driver_number: int,
        current_lap: int,
        tyre_age: int,
        compound: str,
        position: int,
        gap_to_behind: float | None,
        tyre_cliff_lap: int,
        is_safety_car: bool,
        team_name: str = "Unknown",
        total_laps: int = 57,
    ) -> StrategyDecision:
        """
        Make a strategy decision for a competitor.

        Uses team profiles to adjust thresholds and tendencies.
        """
        profile = get_team_profile(team_name)

        # 1. Safety Car Gamble — use team's SC opportunism
        if is_safety_car and will_react_to_safety_car(profile, tyre_age):
            return StrategyDecision(True, "HARD", "Safety Car Opportunity")

        # 2. Tyre Life Critical — if past cliff, must pit
        if tyre_age > tyre_cliff_lap:
            return StrategyDecision(True, "HARD", "Tyre Cliff Reached")

        # 3. Defensive Pit (Cover Undercut) — adjusted by team undercut tendency
        undercut_threshold = 2.0 + (1.0 - profile.undercut_tendency) * 2.0
        min_age_for_cover = max(10, int(15 - profile.undercut_tendency * 5))
        if (
            position <= 10
            and gap_to_behind is not None
            and gap_to_behind < undercut_threshold
            and tyre_age > min_age_for_cover
        ):
            return StrategyDecision(
                True, "HARD", "Covering potential undercut"
            )

        # Default: Stay Out — predict when we'll pit
        predicted_lap = self._estimate_pit_lap(
            current_lap, tyre_age, tyre_cliff_lap, profile, total_laps
        )
        return StrategyDecision(
            False, compound, "Stint ongoing", predicted_pit_lap=predicted_lap
        )

    def predict_pit_lap(
        self,
        state: CompetitorState,
        total_laps: int = 57,
        tyre_cliff_lap: int = 25,
    ) -> tuple[int, float]:
        """
        Predict when a competitor will next pit.

        Returns:
            Tuple of (predicted_lap, confidence 0-1).
        """
        profile = get_team_profile(state.team_name)
        predicted = self._estimate_pit_lap(
            state.current_lap,
            state.tyre_age,
            tyre_cliff_lap,
            profile,
            total_laps,
        )

        # Confidence decreases the further out the prediction is
        laps_away = predicted - state.current_lap
        confidence = max(0.1, min(1.0, 1.0 - laps_away * 0.03))

        return predicted, confidence

    @staticmethod
    def _estimate_pit_lap(
        current_lap: int,
        tyre_age: int,
        tyre_cliff_lap: int,
        profile,
        total_laps: int,
    ) -> int:
        """Estimate the ideal pit lap based on tyre state and team profile."""
        # Base: pit at cliff lap (adjusted by current tyre age offset)
        laps_on_tyre_at_cliff = tyre_cliff_lap
        laps_remaining_in_stint = max(1, laps_on_tyre_at_cliff - tyre_age)
        base_pit_lap = current_lap + laps_remaining_in_stint

        # Adjust for team tendency: early stoppers pit sooner
        bias_shift = int((profile.early_stopper_bias - 0.5) * -4)
        extend_shift = int((profile.extend_stint_tendency - 0.5) * 4)
        adjusted = base_pit_lap + bias_shift + extend_shift

        # Clamp to valid range
        return max(current_lap + 1, min(adjusted, total_laps - 1))
