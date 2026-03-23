"""
Sensitivity analysis for strategy recommendations.

Computes top contributing factors and derives recommendation/confidence
from driver state inputs, for use in the explainability payload.
"""

from __future__ import annotations

from dataclasses import dataclass

from rsw.config.constants import (
    SENSITIVITY_DEG_MULTIPLIER,
    SENSITIVITY_MAX_TOP_FACTORS,
    SENSITIVITY_MIN_FACTOR_SCORE,
    SENSITIVITY_POSITION_THRESHOLD,
    SENSITIVITY_SC_FACTOR_SCORE,
    SENSITIVITY_TYRE_AGE_NORMALIZER,
)

from .decision import evaluate_strategy


@dataclass
class TopFactor:
    name: str
    score: float
    direction: str
    description: str


@dataclass
class SensitivityEntry:
    param_name: str
    confidence_delta: float


@dataclass
class SensitivityResult:
    recommendation: str
    confidence: float
    top_factors: list[TopFactor]
    sensitivity: list[SensitivityEntry]
    what_if_scenarios: list

    def to_dict(self) -> dict:
        return {
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "top_factors": [
                {"name": f.name, "score": f.score, "direction": f.direction, "description": f.description}
                for f in self.top_factors
            ],
            "sensitivity": [
                {"param_name": s.param_name, "confidence_delta": s.confidence_delta}
                for s in self.sensitivity
            ],
            "what_if_scenarios": self.what_if_scenarios,
        }


def _compute_top_factors(
    *,
    deg_slope: float,
    cliff_risk: float,
    tyre_age: int,
    safety_car: bool,
    current_position: int,
    current_lap: int,
    total_laps: int,
) -> list[TopFactor]:
    candidates: list[TopFactor] = []

    deg_score = min((deg_slope or 0.0) * SENSITIVITY_DEG_MULTIPLIER, 1.0)
    if deg_score >= SENSITIVITY_MIN_FACTOR_SCORE:
        candidates.append(TopFactor(
            name="Degradation Rate",
            score=round(deg_score, 3),
            direction="positive",
            description=f"{(deg_slope or 0.0) * 1000:.0f}ms/lap loss — tyre wear accelerating",
        ))

    cliff_score = cliff_risk or 0.0
    if cliff_score >= SENSITIVITY_MIN_FACTOR_SCORE:
        candidates.append(TopFactor(
            name="Cliff Risk",
            score=round(cliff_score, 3),
            direction="positive",
            description="Probability of sudden performance drop",
        ))

    age_score = min((tyre_age or 0) / SENSITIVITY_TYRE_AGE_NORMALIZER, 1.0)
    if age_score >= SENSITIVITY_MIN_FACTOR_SCORE:
        candidates.append(TopFactor(
            name="Tyre Age",
            score=round(age_score, 3),
            direction="positive",
            description=f"{tyre_age} laps on current set",
        ))

    if safety_car:
        candidates.append(TopFactor(
            name="Safety Car",
            score=SENSITIVITY_SC_FACTOR_SCORE,
            direction="positive",
            description="Free pit stop opportunity under safety car",
        ))

    if (current_position or 20) <= SENSITIVITY_POSITION_THRESHOLD:
        candidates.append(TopFactor(
            name="Track Position",
            score=0.4,
            direction="negative",
            description=f"P{current_position} — position value favours staying out",
        ))

    laps_remaining = (total_laps or 50) - (current_lap or 1)
    if laps_remaining < 10:
        fuel_score = min((10 - laps_remaining) / 10.0, 1.0)
        if fuel_score >= SENSITIVITY_MIN_FACTOR_SCORE:
            candidates.append(TopFactor(
                name="Race Distance",
                score=round(fuel_score, 3),
                direction="negative",
                description=f"{laps_remaining} laps left — late race, pitting costly",
            ))

    candidates.sort(key=lambda f: f.score, reverse=True)
    return candidates[:SENSITIVITY_MAX_TOP_FACTORS]


class SensitivityAnalyzer:
    def analyze(
        self,
        *,
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
        rec = evaluate_strategy(
            driver_number=driver_number,
            current_lap=current_lap,
            total_laps=total_laps,
            current_position=current_position,
            deg_slope=deg_slope,
            cliff_risk=cliff_risk,
            current_pace=current_pace,
            tyre_age=tyre_age,
            compound=compound,
            pit_loss=pit_loss,
            gap_to_ahead=gap_to_ahead,
            gap_to_behind=gap_to_behind,
            safety_car=safety_car,
            cliff_age=cliff_age,
        )

        top_factors = _compute_top_factors(
            deg_slope=deg_slope,
            cliff_risk=cliff_risk,
            tyre_age=tyre_age,
            safety_car=safety_car,
            current_position=current_position,
            current_lap=current_lap,
            total_laps=total_laps,
        )

        # Compute per-param sensitivity: perturb each numeric param by +10%
        # and measure |confidence_delta| vs baseline.
        _PERTURBATION = 0.10
        base_conf = rec.confidence
        sensitivity_entries: list[SensitivityEntry] = []
        for param_name, base_val in {
            "pit_loss": pit_loss,
            "deg_slope": deg_slope,
            "cliff_risk": cliff_risk,
        }.items():
            perturbed_val = base_val * (1 + _PERTURBATION)
            if param_name == "cliff_risk":
                perturbed_val = min(perturbed_val, 1.0)
            kwargs = dict(
                driver_number=driver_number,
                current_lap=current_lap,
                total_laps=total_laps,
                current_position=current_position,
                deg_slope=deg_slope,
                cliff_risk=cliff_risk,
                current_pace=current_pace,
                tyre_age=tyre_age,
                compound=compound,
                pit_loss=pit_loss,
                gap_to_ahead=gap_to_ahead,
                gap_to_behind=gap_to_behind,
                safety_car=safety_car,
                cliff_age=cliff_age,
            )
            kwargs[param_name] = perturbed_val
            perturbed_rec = evaluate_strategy(**kwargs)
            delta = abs(perturbed_rec.confidence - base_conf)
            sensitivity_entries.append(SensitivityEntry(
                param_name=param_name,
                confidence_delta=round(delta, 4),
            ))

        return SensitivityResult(
            recommendation=rec.recommendation.value,
            confidence=round(rec.confidence, 3),
            top_factors=top_factors,
            sensitivity=sensitivity_entries,
            what_if_scenarios=[],
        )
