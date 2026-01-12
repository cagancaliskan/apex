"""
Competitor AI Strategy Engine.

Simulates rational decision making for rival drivers.
Instead of random pit stops, rivals will:
1. Pit when tyres are dead (Cliff).
2. Cover undercuts if they are threatened.
3. Gamble on Safety Cars.
"""

from dataclasses import dataclass


@dataclass
class StrategyDecision:
    should_pit: bool
    compound: str
    reason: str


class CompetitorAI:
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
    ) -> StrategyDecision:
        """
        Make a strategy decision for a competitor.
        """

        # 1. Safety Car Gamble
        # If SC and tyres are somewhat old (>10 laps), cheap pit stop!
        if is_safety_car and tyre_age > 10:
            return StrategyDecision(True, "HARD", "Safety Car Opportunity")

        # 2. Tyre Life Critical
        # If past cliff, must pit.
        if tyre_age > tyre_cliff_lap:
            return StrategyDecision(True, "HARD", "Tyre Cliff Reached")

        # 3. Defensive Pit (Cover Undercut)
        # Simplified: If top 10 and gap to behind is small (<2s) and window is open (>15 laps)
        if position <= 10 and gap_to_behind is not None and gap_to_behind < 2.0 and tyre_age > 15:
            # 50% chance to cover immediately (simulate reaction time/strategy variance)
            # In a real engine this would check 'if pitting keeps me ahead'
            return StrategyDecision(True, "HARD", "Covering potential undercut")

        # Default: Stay Out
        return StrategyDecision(False, compound, "Stint ongoing")
