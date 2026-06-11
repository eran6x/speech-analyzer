"""Rule-based scoring (1-100).

Every tunable number lives in CONFIG so ideal ranges and weights stay in one
place (per the project conventions). Scores that depend on acoustic features are
only produced when those features are present; otherwise they're left None and
dropped from the overall blend.

The numbers say *what*; the coaching layer says *why and how to fix it*.
"""

from __future__ import annotations

from statistics import mean
from typing import Optional

from .models import Metrics, Scores

MIN_SCORE = 1
MAX_SCORE = 100

CONFIG = {
    # wpm: full marks inside the ideal band, ramping to MIN at the floors.
    "pace": {"ideal_min": 130, "ideal_max": 160, "floor_low": 80, "floor_high": 210},
    # silent pauses per minute: too few = rushing, too many = choppy/hesitant.
    "pauses": {
        "ideal_min": 4,
        "ideal_max": 12,
        "floor_low": 0,
        "floor_high": 28,
        "filler_penalty_per_density": 4.0,  # points per filler-per-100-words
    },
    # confidence: pitch expressiveness + volume projection + steadiness, minus hedging.
    "confidence": {
        # F0 std dev (Hz): monotone = disengaging, healthy variation = expressive.
        "pitch_var": {"ideal_min": 20, "ideal_max": 60, "floor_low": 3, "floor_high": 120},
        # mean intensity (dB) → projection. Relative proxy; mic-gain dependent.
        "projection": {"floor_db": 50.0, "target_db": 70.0},
        # intensity std dev (dB) → steadiness. Lower is steadier.
        "steadiness": {"best_db": 3.0, "worst_db": 12.0},
        "hedge_penalty_per": 5.0,
        "upspeak_penalty_per": 6.0,  # rising declarative endings undermine authority
    },
    # fluency: penalize fillers and false starts off a clean baseline.
    "fluency": {
        "filler_penalty_per_density": 6.0,
        "false_start_penalty_per": 4.0,
    },
    # overall: equal-weighted blend of whichever dimensions are available.
    "weights": {"pace": 1.0, "pauses": 1.0, "confidence": 1.0, "fluency": 1.0},
}


def _clamp(value: float) -> int:
    return int(max(MIN_SCORE, min(MAX_SCORE, round(value))))


def _band_score(value: float, floor_low: float, ideal_min: float,
                ideal_max: float, floor_high: float) -> int:
    """MAX inside [ideal_min, ideal_max], ramping linearly to MIN at the floors."""
    if ideal_min <= value <= ideal_max:
        return MAX_SCORE
    if value < ideal_min:
        span = ideal_min - floor_low
        frac = (value - floor_low) / span if span > 0 else 0.0
    else:
        span = floor_high - ideal_max
        frac = (floor_high - value) / span if span > 0 else 0.0
    return _clamp(MIN_SCORE + frac * (MAX_SCORE - MIN_SCORE))


def score_pace(wpm: float) -> int:
    c = CONFIG["pace"]
    return _band_score(wpm, c["floor_low"], c["ideal_min"], c["ideal_max"], c["floor_high"])


def score_pauses(pause_count: int, duration_sec: float, filler_density: float) -> int:
    c = CONFIG["pauses"]
    per_min = (pause_count / duration_sec * 60.0) if duration_sec > 0 else 0.0
    base = _band_score(per_min, c["floor_low"], c["ideal_min"], c["ideal_max"], c["floor_high"])
    penalty = filler_density * c["filler_penalty_per_density"]
    return _clamp(base - penalty)


def score_confidence(metrics: Metrics) -> Optional[int]:
    # Requires acoustic features; without them confidence is undefined.
    if metrics.pitch_variability is None or metrics.mean_intensity_db is None:
        return None
    c = CONFIG["confidence"]

    pv = c["pitch_var"]
    pitch_score = _band_score(
        metrics.pitch_variability, pv["floor_low"], pv["ideal_min"],
        pv["ideal_max"], pv["floor_high"],
    )

    proj = c["projection"]
    proj_frac = (metrics.mean_intensity_db - proj["floor_db"]) / (
        proj["target_db"] - proj["floor_db"]
    )
    projection_score = _clamp(proj_frac * MAX_SCORE)

    steady = c["steadiness"]
    stab = metrics.volume_stability if metrics.volume_stability is not None else steady["worst_db"]
    steady_frac = 1.0 - (stab - steady["best_db"]) / (steady["worst_db"] - steady["best_db"])
    steadiness_score = _clamp(steady_frac * MAX_SCORE)

    composite = mean([pitch_score, projection_score, steadiness_score])
    hedge_penalty = (metrics.hedge_count or 0) * c["hedge_penalty_per"]
    upspeak_penalty = (metrics.upspeak_count or 0) * c["upspeak_penalty_per"]
    return _clamp(composite - hedge_penalty - upspeak_penalty)


def score_fluency(metrics: Metrics) -> int:
    c = CONFIG["fluency"]
    filler_density = metrics.filler_density or 0.0
    false_starts = metrics.false_start_count or 0
    penalty = (
        filler_density * c["filler_penalty_per_density"]
        + false_starts * c["false_start_penalty_per"]
    )
    return _clamp(MAX_SCORE - penalty)


def compute_scores(metrics: Metrics, duration_sec: float) -> Scores:
    pace = score_pace(metrics.wpm)
    pauses = score_pauses(metrics.pause_count, duration_sec, metrics.filler_density or 0.0)
    confidence = score_confidence(metrics)
    fluency = score_fluency(metrics)

    weights = CONFIG["weights"]
    dims = {"pace": pace, "pauses": pauses, "confidence": confidence, "fluency": fluency}
    available = {k: v for k, v in dims.items() if v is not None}
    total_weight = sum(weights[k] for k in available)
    overall = (
        _clamp(sum(weights[k] * v for k, v in available.items()) / total_weight)
        if total_weight > 0
        else pace
    )

    return Scores(
        pace=pace,
        pauses=pauses,
        confidence=confidence,
        fluency=fluency,
        overall=overall,
    )
