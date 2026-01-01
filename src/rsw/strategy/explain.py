"""
Natural language explanations for strategy recommendations.

Generates human-readable explanations that help engineers
understand and communicate strategy decisions.
"""

from .decision import StrategyRecommendation, RecommendationType
from .pit_window import PitWindow


def explain_recommendation(rec: StrategyRecommendation) -> str:
    """
    Generate human-readable explanation of a strategy recommendation.
    
    Args:
        rec: Strategy recommendation to explain
    
    Returns:
        Multi-line explanation string
    """
    lines = []
    
    # Header
    if rec.recommendation == RecommendationType.PIT_NOW:
        lines.append(f"🔴 PIT NOW - Confidence: {rec.confidence:.0%}")
    elif rec.recommendation == RecommendationType.CONSIDER_PIT:
        lines.append(f"🟡 CONSIDER PIT - Confidence: {rec.confidence:.0%}")
    elif rec.recommendation == RecommendationType.STAY_OUT:
        lines.append(f"🟢 STAY OUT - Confidence: {rec.confidence:.0%}")
    else:
        lines.append(f"🟢 EXTEND STINT - Confidence: {rec.confidence:.0%}")
    
    lines.append("")
    
    # Main reason
    lines.append(f"📋 {rec.reason}")
    
    # Window info
    if rec.pit_window and rec.pit_window.ideal_lap > 0:
        w = rec.pit_window
        lines.append(f"🎯 Pit Window: Laps {w.min_lap}-{w.max_lap} (ideal: {w.ideal_lap})")
    
    # Threats
    if rec.undercut_threat:
        lines.append("⚠️ UNDERCUT THREAT - Car ahead is slow, we can pass")
    if rec.overcut_opportunity:
        lines.append("💡 Overcut viable - we're preserving tyres better")
    
    # Pit decision details
    if rec.pit_decision:
        d = rec.pit_decision
        lines.append(f"📊 Pit to {d.compound_to}")
        if d.expected_positions_lost > 0:
            lines.append(f"   ↓ May lose {d.expected_positions_lost} position(s)")
        lines.append(f"   ⏱️ Expected gain: {d.expected_time_gain:.1f}s over stint")
    
    # Alternatives
    if rec.alternatives:
        lines.append("")
        lines.append("🔄 Alternatives:")
        for alt in rec.alternatives:
            lines.append(f"   • {alt}")
    
    return "\n".join(lines)


def explain_pit_window(window: PitWindow) -> str:
    """Explain pit window in simple terms."""
    if window.ideal_lap == 0:
        return "No pit stop recommended - stay out to finish"
    
    width = window.max_lap - window.min_lap
    
    if width <= 3:
        urgency = "Narrow window - pit soon"
    elif width <= 8:
        urgency = "Moderate flexibility"
    else:
        urgency = "Wide window - flexible timing"
    
    return f"Pit between laps {window.min_lap}-{window.max_lap}. {urgency}"


def explain_cliff_risk(cliff_risk: float, compound: str) -> str:
    """Explain tyre cliff risk."""
    if cliff_risk < 0.3:
        return f"{compound} tyres performing well, no immediate concern"
    elif cliff_risk < 0.6:
        return f"{compound} tyres showing degradation, monitor closely"
    elif cliff_risk < 0.8:
        return f"⚠️ {compound} tyres approaching cliff - consider pitting soon"
    else:
        return f"🔴 {compound} at cliff! Performance drop imminent - pit immediately"


def explain_undercut(gap_ahead: float, pit_loss: float, fresh_advantage: float) -> str:
    """Explain undercut opportunity."""
    gap_after_pit = gap_ahead - pit_loss
    
    if gap_after_pit > 0:
        return f"Undercut not viable - would emerge {-gap_after_pit:.1f}s behind"
    
    laps_to_pass = abs(gap_after_pit) / max(fresh_advantage, 0.1)
    return f"Undercut possible - ~{laps_to_pass:.0f} laps to complete move"


def explain_safety_car_opportunity(
    in_window: bool,
    gap_to_behind: float | None,
    pit_loss: float,
) -> str:
    """Explain safety car pit opportunity."""
    if not in_window:
        return "Safety car but outside pit window - stay out"
    
    if gap_to_behind and gap_to_behind > pit_loss * 0.4:
        return "✅ Safety car PIT - free stop, won't lose position"
    
    return "Safety car PIT - may lose position but worth it"


def format_strategy_summary(rec: StrategyRecommendation) -> dict:
    """
    Format recommendation for JSON/frontend consumption.
    
    Returns dict with:
        - action: "PIT_NOW", "STAY_OUT", etc.
        - confidence: 0-1 float
        - reason: short string
        - window: {min, max, ideal} or null
        - threats: {undercut, overcut}
    """
    window_dict = None
    if rec.pit_window and rec.pit_window.ideal_lap > 0:
        window_dict = {
            "min": rec.pit_window.min_lap,
            "max": rec.pit_window.max_lap,
            "ideal": rec.pit_window.ideal_lap,
        }
    
    return {
        "action": rec.recommendation.value,
        "confidence": round(rec.confidence, 2),
        "reason": rec.reason,
        "window": window_dict,
        "threats": {
            "undercut": rec.undercut_threat,
            "overcut": rec.overcut_opportunity,
        },
        "pit_to": rec.pit_decision.compound_to if rec.pit_decision else None,
    }
