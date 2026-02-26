"""
Sensitivity Analyzer for explainable strategy recommendations.

Provides:
1. Factor ranking — top 3 factors driving the recommendation
2. Sensitivity analysis — reruns evaluate_strategy with perturbed params
3. What-if scenarios — human-readable descriptions of alternative outcomes
"""

from dataclasses import dataclass, field
from typing import Any

from .decision import RecommendationType, StrategyRecommendation, evaluate_strategy


@dataclass
class FactorContribution:
    """A single factor contributing to the recommendation."""

    name: str
    score: float  # 0-1 contribution magnitude
    direction: str  # "positive" = pushes toward pit, "negative" = pushes to stay out
    description: str


@dataclass
class SensitivityPoint:
    """Result of perturbing a single parameter."""

    param_name: str
    param_label: str  # Human-readable
    low_value: float
    base_value: float
    high_value: float
    low_recommendation: str
    base_recommendation: str
    high_recommendation: str
    low_confidence: float
    base_confidence: float
    high_confidence: float
    confidence_delta: float  # max change in confidence


@dataclass
class WhatIfScenario:
    """A single what-if scenario."""

    condition: str  # "If pit loss were 24s..."
    outcome: str  # "recommendation changes to STAY_OUT"
    confidence_change: float  # -0.15 means 15% drop


@dataclass
class SensitivityResult:
    """Complete sensitivity analysis output."""

    recommendation: str
    confidence: float
    top_factors: list[FactorContribution] = field(default_factory=list)
    sensitivity: list[SensitivityPoint] = field(default_factory=list)
    what_if_scenarios: list[WhatIfScenario] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation": self.recommendation,
            "confidence": round(self.confidence, 3),
            "top_factors": [
                {
                    "name": f.name,
                    "score": round(f.score, 3),
                    "direction": f.direction,
                    "description": f.description,
                }
                for f in self.top_factors
            ],
            "sensitivity": [
                {
                    "param_name": s.param_name,
                    "param_label": s.param_label,
                    "low_value": round(s.low_value, 2),
                    "base_value": round(s.base_value, 2),
                    "high_value": round(s.high_value, 2),
                    "low_rec": s.low_recommendation,
                    "base_rec": s.base_recommendation,
                    "high_rec": s.high_recommendation,
                    "low_conf": round(s.low_confidence, 3),
                    "base_conf": round(s.base_confidence, 3),
                    "high_conf": round(s.high_confidence, 3),
                    "delta": round(s.confidence_delta, 3),
                }
                for s in self.sensitivity
            ],
            "what_if_scenarios": [
                {
                    "condition": w.condition,
                    "outcome": w.outcome,
                    "confidence_change": round(w.confidence_change, 3),
                }
                for w in self.what_if_scenarios
            ],
        }


class SensitivityAnalyzer:
    """
    Analyzes strategy recommendations to surface:
    - Which factors matter most
    - How sensitive the recommendation is to parameter changes
    - What would change if assumptions are wrong
    """

    # Perturbation ranges
    PERTURBATIONS = {
        "pit_loss": {"label": "Pit Stop Loss", "delta": 2.0},
        "deg_slope": {"label": "Tyre Degradation Rate", "delta": 0.02},
        "cliff_risk": {"label": "Cliff Risk Score", "delta": 0.15},
    }

    def analyze(
        self,
        driver_number: int,
        current_lap: int,
        total_laps: int,
        current_position: int,
        deg_slope: float,
        cliff_risk: float,
        current_pace: float,
        tyre_age: int,
        compound: str,
        pit_loss: float,
        gap_to_ahead: float | None = None,
        gap_to_behind: float | None = None,
        safety_car: bool = False,
        cliff_age: int | None = None,
    ) -> SensitivityResult:
        """Run full sensitivity analysis on a strategy recommendation."""

        # 1. Get base recommendation
        base_params = {
            "driver_number": driver_number,
            "current_lap": current_lap,
            "total_laps": total_laps,
            "current_position": current_position,
            "deg_slope": deg_slope,
            "cliff_risk": cliff_risk,
            "current_pace": current_pace,
            "tyre_age": tyre_age,
            "compound": compound,
            "pit_loss": pit_loss,
            "gap_to_ahead": gap_to_ahead,
            "gap_to_behind": gap_to_behind,
            "safety_car": safety_car,
            "cliff_age": cliff_age,
        }

        base_rec = evaluate_strategy(**base_params)

        # 2. Rank factors
        top_factors = self._rank_factors(base_rec, base_params)

        # 3. Run sensitivity analysis
        sensitivity = self._run_sensitivity(base_rec, base_params)

        # 4. Generate what-if scenarios
        what_ifs = self._generate_what_ifs(base_rec, sensitivity)

        return SensitivityResult(
            recommendation=base_rec.recommendation.value,
            confidence=base_rec.confidence,
            top_factors=top_factors,
            sensitivity=sensitivity,
            what_if_scenarios=what_ifs,
        )

    def _rank_factors(
        self,
        base_rec: StrategyRecommendation,
        params: dict[str, Any],
    ) -> list[FactorContribution]:
        """Rank the top factors driving the recommendation."""
        factors: list[FactorContribution] = []

        remaining_laps = params["total_laps"] - params["current_lap"]
        cliff_risk = params["cliff_risk"]
        tyre_age = params["tyre_age"]
        deg_slope = params["deg_slope"]

        # Cliff risk factor
        if cliff_risk > 0.3:
            factors.append(FactorContribution(
                name="Cliff Risk",
                score=min(1.0, cliff_risk),
                direction="positive",
                description=f"Tyre cliff risk at {cliff_risk:.0%} — {'critical' if cliff_risk > 0.7 else 'elevated'}",
            ))

        # Remaining laps factor
        remaining_factor = 1.0 - min(1.0, remaining_laps / 15)
        if remaining_laps <= 15:
            factors.append(FactorContribution(
                name="Race Ending",
                score=remaining_factor,
                direction="negative",
                description=f"Only {remaining_laps} laps remaining — pit value diminishing",
            ))

        # Degradation rate factor
        deg_factor = min(1.0, deg_slope / 0.12)
        if deg_slope > 0.04:
            factors.append(FactorContribution(
                name="Degradation Rate",
                score=deg_factor,
                direction="positive",
                description=f"Losing {deg_slope:.3f}s/lap — {'high' if deg_slope > 0.08 else 'moderate'} degradation",
            ))

        # Undercut threat
        if base_rec.undercut_threat:
            factors.append(FactorContribution(
                name="Undercut Threat",
                score=0.7,
                direction="positive",
                description="Car ahead is vulnerable — undercut opportunity window open",
            ))

        # Overcut opportunity
        if base_rec.overcut_opportunity:
            factors.append(FactorContribution(
                name="Overcut Opportunity",
                score=0.5,
                direction="negative",
                description="Better tyre management than car behind — overcut viable",
            ))

        # Safety car
        if params["safety_car"]:
            factors.append(FactorContribution(
                name="Safety Car",
                score=0.95,
                direction="positive",
                description="Safety car deployed — free pit stop opportunity",
            ))

        # Tyre age
        tyre_factor = min(1.0, tyre_age / 30)
        if tyre_age > 10:
            factors.append(FactorContribution(
                name="Tyre Age",
                score=tyre_factor,
                direction="positive",
                description=f"Tyres are {tyre_age} laps old on {params['compound']}",
            ))

        # Sort by score descending, take top 3
        factors.sort(key=lambda f: f.score, reverse=True)
        return factors[:3]

    def _run_sensitivity(
        self,
        base_rec: StrategyRecommendation,
        params: dict[str, Any],
    ) -> list[SensitivityPoint]:
        """Run strategy evaluation with perturbed parameters."""
        results = []

        for param_name, config in self.PERTURBATIONS.items():
            base_value = params[param_name]
            delta = config["delta"]

            # Low perturbation
            low_params = {**params, param_name: max(0.0, base_value - delta)}
            low_rec = evaluate_strategy(**low_params)

            # High perturbation
            high_params = {**params, param_name: base_value + delta}
            high_rec = evaluate_strategy(**high_params)

            confidence_delta = max(
                abs(low_rec.confidence - base_rec.confidence),
                abs(high_rec.confidence - base_rec.confidence),
            )

            results.append(SensitivityPoint(
                param_name=param_name,
                param_label=config["label"],
                low_value=max(0.0, base_value - delta),
                base_value=base_value,
                high_value=base_value + delta,
                low_recommendation=low_rec.recommendation.value,
                base_recommendation=base_rec.recommendation.value,
                high_recommendation=high_rec.recommendation.value,
                low_confidence=low_rec.confidence,
                base_confidence=base_rec.confidence,
                high_confidence=high_rec.confidence,
                confidence_delta=confidence_delta,
            ))

        # Sort by impact
        results.sort(key=lambda s: s.confidence_delta, reverse=True)
        return results

    def _generate_what_ifs(
        self,
        base_rec: StrategyRecommendation,
        sensitivity: list[SensitivityPoint],
    ) -> list[WhatIfScenario]:
        """Generate human-readable what-if scenarios from sensitivity data."""
        scenarios: list[WhatIfScenario] = []

        for s in sensitivity:
            # Check if low perturbation changes recommendation
            if s.low_recommendation != s.base_recommendation:
                scenarios.append(WhatIfScenario(
                    condition=f"If {s.param_label.lower()} were {s.low_value:.2f} instead of {s.base_value:.2f}",
                    outcome=f"recommendation changes to {s.low_recommendation}",
                    confidence_change=round(s.low_confidence - s.base_confidence, 3),
                ))

            # Check if high perturbation changes recommendation
            if s.high_recommendation != s.base_recommendation:
                scenarios.append(WhatIfScenario(
                    condition=f"If {s.param_label.lower()} were {s.high_value:.2f} instead of {s.base_value:.2f}",
                    outcome=f"recommendation changes to {s.high_recommendation}",
                    confidence_change=round(s.high_confidence - s.base_confidence, 3),
                ))

            # Even if recommendation doesn't change, note big confidence shifts
            if s.confidence_delta > 0.1 and s.high_recommendation == s.base_recommendation:
                scenarios.append(WhatIfScenario(
                    condition=f"If {s.param_label.lower()} increased to {s.high_value:.2f}",
                    outcome=f"confidence shifts by {s.high_confidence - s.base_confidence:+.0%}",
                    confidence_change=round(s.high_confidence - s.base_confidence, 3),
                ))

        return scenarios[:5]  # Limit to 5 most impactful
