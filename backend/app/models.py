"""Pydantic schemas shared across the backend.

Phase 1 only populates a subset of the full data model described in the
project brief (wpm, pause_count, pace score). The remaining fields are kept
optional so future phases can fill them in without changing the contract.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Topic(BaseModel):
    category: str
    prompt: str


class Metrics(BaseModel):
    """Acoustic + transcript metrics. Phase 1 fills wpm and pause_count."""

    wpm: float = Field(..., description="Words per minute, including pauses")
    pause_count: int = Field(..., description="Silent gaps between words over the threshold")

    # --- Reserved for later phases (see Speech_analyer_plan.md) ---
    articulation_rate: Optional[float] = None
    mean_pitch_hz: Optional[float] = None
    pitch_variability: Optional[float] = None
    mean_intensity_db: Optional[float] = None
    volume_stability: Optional[float] = None
    mean_pause_sec: Optional[float] = None
    filler_count: Optional[int] = None
    filler_density: Optional[float] = None
    false_start_count: Optional[int] = None
    upspeak_count: Optional[int] = None
    hedge_count: Optional[int] = None
    jitter: Optional[float] = None       # local jitter (fraction)
    shimmer: Optional[float] = None      # local shimmer (fraction)
    hnr: Optional[float] = None          # harmonics-to-noise ratio (dB)


class Scores(BaseModel):
    """1-100 scores. Phase 1 computes pace; others arrive in later phases."""

    pace: int = Field(..., ge=1, le=100)
    pauses: Optional[int] = Field(None, ge=1, le=100)
    confidence: Optional[int] = Field(None, ge=1, le=100)
    fluency: Optional[int] = Field(None, ge=1, le=100)
    overall: Optional[int] = Field(None, ge=1, le=100)


class Annotation(BaseModel):
    """A time span in the recording worth marking on playback."""

    kind: str  # pause | filler | hedge | upspeak
    label: str
    start: float
    end: float


class Session(BaseModel):
    id: str
    timestamp: str
    topic: Topic
    duration_sec: float
    transcript: str
    metrics: Metrics
    scores: Scores
    feedback: Optional[str] = None
    audio_path: Optional[str] = None
    # Optional so sessions saved before Phase 3 still load.
    annotations: Optional[list[Annotation]] = None


class Averages(BaseModel):
    overall: Optional[float] = None
    pace: Optional[float] = None
    pauses: Optional[float] = None
    confidence: Optional[float] = None
    fluency: Optional[float] = None


class Stats(BaseModel):
    total_sessions: int
    current_streak: int
    longest_streak: int
    sessions_this_week: int
    averages: Averages
