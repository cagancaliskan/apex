"""
Backtest metrics for strategy evaluation.

Calculates how well the strategy recommendations would have performed
compared to actual race outcomes.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PitDecisionResult:
    """Result of a single pit decision."""
    driver_number: int
    lap: int
    recommended_action: str  # PIT_NOW, STAY_OUT, etc.
    actual_action: str  # PITTED, STAYED_OUT
    was_correct: bool
    position_before: int
    position_after: int
    position_delta: int


@dataclass
class BacktestReport:
    """Complete backtest report for a session."""
    session_key: int
    session_name: str
    total_laps: int
    
    # Decision accuracy
    total_decisions: int = 0
    correct_decisions: int = 0
    accuracy: float = 0.0
    
    # Pit timing
    pit_decisions: list[PitDecisionResult] = field(default_factory=list)
    avg_pit_timing_error: float = 0.0  # Laps early/late vs optimal
    
    # Position gains
    total_position_gain: int = 0
    avg_position_gain: float = 0.0
    
    # Per-driver summaries
    driver_summaries: dict[int, dict] = field(default_factory=dict)


def calculate_metrics(
    recommendations: list[dict],
    actual_pits: list[dict],
    position_history: dict[int, list[int]],
) -> BacktestReport:
    """
    Calculate backtest metrics comparing recommendations to actual race.
    
    Args:
        recommendations: List of {lap, driver_number, action, optimal_pit_lap}
        actual_pits: List of {driver_number, lap_number}
        position_history: {driver_number: [position at each lap]}
    
    Returns:
        BacktestReport with metrics
    """
    report = BacktestReport(
        session_key=0,
        session_name="Unknown",
        total_laps=0,
    )
    
    # Track pit laps by driver
    actual_pit_laps: dict[int, list[int]] = {}
    for pit in actual_pits:
        driver = pit["driver_number"]
        lap = pit["lap_number"]
        if driver not in actual_pit_laps:
            actual_pit_laps[driver] = []
        actual_pit_laps[driver].append(lap)
    
    # Analyze each recommendation
    for rec in recommendations:
        lap = rec.get("lap", 0)
        driver = rec.get("driver_number", 0)
        action = rec.get("action", "")
        optimal_lap = rec.get("optimal_pit_lap", 0)
        
        # Check if driver actually pitted within window
        driver_pits = actual_pit_laps.get(driver, [])
        pitted_this_window = any(abs(p - lap) <= 2 for p in driver_pits)
        
        # Determine if recommendation was correct
        was_correct = False
        if action == "PIT_NOW" and pitted_this_window:
            was_correct = True
        elif action == "STAY_OUT" and not pitted_this_window:
            was_correct = True
        
        # Get position change
        positions = position_history.get(driver, [])
        pos_before = positions[lap - 1] if lap > 0 and lap <= len(positions) else 0
        pos_after = positions[lap] if lap < len(positions) else pos_before
        pos_delta = pos_before - pos_after  # Positive = gained positions
        
        result = PitDecisionResult(
            driver_number=driver,
            lap=lap,
            recommended_action=action,
            actual_action="PITTED" if pitted_this_window else "STAYED_OUT",
            was_correct=was_correct,
            position_before=pos_before,
            position_after=pos_after,
            position_delta=pos_delta,
        )
        
        report.pit_decisions.append(result)
        report.total_decisions += 1
        if was_correct:
            report.correct_decisions += 1
        report.total_position_gain += pos_delta
    
    # Calculate summary stats
    if report.total_decisions > 0:
        report.accuracy = report.correct_decisions / report.total_decisions
        report.avg_position_gain = report.total_position_gain / report.total_decisions
    
    # Calculate pit timing error
    timing_errors = []
    for rec in recommendations:
        if rec.get("optimal_pit_lap", 0) > 0:
            driver = rec.get("driver_number", 0)
            actual = actual_pit_laps.get(driver, [])
            if actual:
                error = min(abs(a - rec["optimal_pit_lap"]) for a in actual)
                timing_errors.append(error)
    
    if timing_errors:
        report.avg_pit_timing_error = sum(timing_errors) / len(timing_errors)
    
    return report


def format_report(report: BacktestReport) -> str:
    """Format backtest report as readable string."""
    lines = [
        "=" * 60,
        f"BACKTEST REPORT - {report.session_name}",
        "=" * 60,
        "",
        f"Total Decisions: {report.total_decisions}",
        f"Correct Decisions: {report.correct_decisions}",
        f"Accuracy: {report.accuracy:.1%}",
        "",
        f"Avg Pit Timing Error: {report.avg_pit_timing_error:.1f} laps",
        f"Total Position Gain: {report.total_position_gain:+d}",
        f"Avg Position Gain: {report.avg_position_gain:+.2f}",
        "",
    ]
    
    if report.pit_decisions:
        lines.append("Recent Decisions:")
        for dec in report.pit_decisions[-5:]:
            correct = "✓" if dec.was_correct else "✗"
            lines.append(
                f"  {correct} Lap {dec.lap}: #{dec.driver_number} "
                f"recommended {dec.recommended_action}, "
                f"driver {dec.actual_action} (Δ{dec.position_delta:+d})"
            )
    
    lines.append("=" * 60)
    return "\n".join(lines)
