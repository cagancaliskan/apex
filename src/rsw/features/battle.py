"""
Battle & Overtake Probability — uses neural model outputs to estimate
the likelihood of an on-track overtake within the current lap.

Consumed by LiveRaceService._run_strategy_update() after degradation
predictions have been computed for all drivers.
"""

from __future__ import annotations

COMPOUND_RANK: dict[str, int] = {
    "SOFT": 4,
    "MEDIUM": 3,
    "HARD": 2,
    "INTERMEDIATE": 1,
    "WET": 0,
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_overtake_probability(
    gap: float,
    drs_attacker: int,
    pace_next_attacker: float,
    pace_next_defender: float,
    cliff_risk_defender: float,
    attacker_tyre_age: int,
    defender_tyre_age: int,
    attacker_compound: str,
    defender_compound: str,
) -> tuple[float, str]:
    """
    Estimate the probability of an overtake occurring this lap.

    Uses neural model outputs (predicted_pace[0], cliff_risk) already
    computed per driver in the strategy update loop.

    Args:
        gap: gap_to_ahead in seconds (attacker's gap to the car ahead)
        drs_attacker: DRS state of attacker (0=off, 8=available, 10/12/14=active)
        pace_next_attacker: neural predicted next-lap pace correction for attacker
        pace_next_defender: neural predicted next-lap pace correction for defender
        cliff_risk_defender: 0–1 cliff probability for the driver being attacked
        attacker_tyre_age: laps on current attacker tyre set
        defender_tyre_age: laps on current defender tyre set
        attacker_compound: tyre compound string for attacker
        defender_compound: tyre compound string for defender

    Returns:
        (probability, key_factor_label) — probability clamped to [0.05, 0.95]
    """
    base = 0.25

    # 1. Gap factor — closer gap raises probability (linear, max +0.15 at 0 s)
    gap_factor = max(0.0, (1.5 - gap) / 1.5) * 0.15

    # 2. DRS factor
    if drs_attacker in (10, 12, 14):
        drs_factor = 0.20
        drs_label = "DRS active"
    elif drs_attacker == 8:
        drs_factor = 0.10
        drs_label = "DRS available"
    else:
        drs_factor = 0.0
        drs_label = ""

    # 3. Neural pace delta (next lap): positive = attacker predicted faster
    # pace corrections are seconds vs base; higher = slower; lower = faster
    pace_delta = pace_next_defender - pace_next_attacker
    pace_factor = _clamp(pace_delta * 0.05, -0.12, 0.12)

    # 4. Cliff risk of the defender (neural output) — higher risk = more likely to be passed
    cliff_factor = cliff_risk_defender * 0.15

    # 5. Compound advantage (attacker compound rank minus defender rank)
    att_rank = COMPOUND_RANK.get(attacker_compound.upper(), 2)
    def_rank = COMPOUND_RANK.get(defender_compound.upper(), 2)
    comp_delta = att_rank - def_rank
    compound_factor = _clamp(comp_delta * 0.08, -0.15, 0.15)

    # 6. Tyre age delta — attacker fresher = advantage (positive age_delta)
    age_delta = defender_tyre_age - attacker_tyre_age
    age_factor = _clamp(age_delta * 0.012, -0.10, 0.10)

    prob = _clamp(
        base + gap_factor + drs_factor + pace_factor + cliff_factor + compound_factor + age_factor,
        0.05,
        0.95,
    )

    # Determine the single highest-contributing factor label
    factors: list[tuple[float, str]] = [
        (drs_factor, drs_label),
        (cliff_factor, "cliff risk ahead"),
        (pace_factor, "pace advantage"),
        (compound_factor, "compound edge"),
        (age_factor, f"+{age_delta} laps fresher" if age_delta >= 6 else ""),
    ]
    # Filter to positive, labelled factors; fall back to "gap closing"
    labelled = [(v, lbl) for v, lbl in factors if v >= 0.06 and lbl]
    if labelled:
        key_factor = max(labelled, key=lambda x: x[0])[1]
    else:
        key_factor = "gap closing"

    return round(prob, 3), key_factor
