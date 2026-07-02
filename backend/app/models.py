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


class GenerationUsage(BaseModel):
    """Token/cost accounting for one ideal-delivery generation.

    Style tokens (Claude) are exact; TTS cost is an *estimate* — OpenAI's speech
    endpoint returns no usage, so it's derived from characters + audio length.
    """

    provider: str
    model: Optional[str] = None
    # Delivery-style LLM (Claude) — exact from the Messages API usage.
    style_input_tokens: Optional[int] = None
    style_output_tokens: Optional[int] = None
    style_cost_usd: Optional[float] = None
    # Text-to-speech — estimated.
    tts_characters: Optional[int] = None
    tts_audio_seconds: Optional[float] = None
    tts_cost_usd: Optional[float] = None  # None = plan-dependent (ElevenLabs)
    total_cost_usd: Optional[float] = None
    estimated: bool = True


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
    # Phase 6: generated "ideal delivery" audio in the user's cloned voice.
    ideal_audio_path: Optional[str] = None
    delivery_style: Optional[str] = None
    generation_usage: Optional[GenerationUsage] = None
    # Phase 7: coaching/scoring target (speaker profile or style goal) in effect.
    coaching_target: Optional[str] = None
    # Phase 8: retake linking — the attempt this one improves on, and its number.
    parent_id: Optional[str] = None
    attempt: int = 1


class TranscriptUpdate(BaseModel):
    transcript: str


class TargetBands(BaseModel):
    """Target metric bands [lo, hi] for a coaching target (None = not steered)."""

    wpm: Optional[list[float]] = None
    pitch_variability_hz: Optional[list[float]] = None
    pauses_per_min: Optional[list[float]] = None


class TargetInfo(BaseModel):
    id: str
    name: str
    kind: str  # speaker | style | balanced
    blurb: str
    bands: TargetBands
    style_notes: str


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
