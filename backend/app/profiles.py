"""Curated coaching targets — famous-speaker profiles and style goals.

Each target carries optional metric bands [lo, hi] (the single source of truth
for both the you-vs-them comparison and target-relative scoring in scoring.py)
plus qualitative style notes that flavor the coaching + ideal-delivery prompts.

Bands are curated approximations, not measured from audio — tune them freely.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import TargetBands, TargetInfo

Band = Optional[tuple[float, float]]


@dataclass(frozen=True)
class _Target:
    id: str
    name: str
    kind: str  # speaker | style | balanced
    blurb: str
    style_notes: str
    wpm: Band = None
    pitch_variability_hz: Band = None
    pauses_per_min: Band = None


_TARGETS: list[_Target] = [
    _Target(
        "balanced", "Balanced", "balanced",
        "Well-rounded, natural delivery (default).",
        "Clear, varied, and natural — no single style imposed.",
    ),
    # --- Speaker profiles ---
    _Target(
        "jobs", "Steve Jobs", "speaker",
        "Deliberate, dramatic, reveal-driven.",
        "Deliberate pace with dramatic pauses before key points; plain words; "
        "build-up and reveal; land one idea at a time with strong emphasis.",
        wpm=(120, 140), pitch_variability_hz=(30, 70), pauses_per_min=(10, 18),
    ),
    _Target(
        "obama", "Barack Obama", "speaker",
        "Measured cadence and calm authority.",
        "Measured cadence, generous rhetorical pauses, wide but controlled pitch, "
        "tricolon and repetition, calm authority.",
        wpm=(110, 135), pitch_variability_hz=(35, 80), pauses_per_min=(10, 20),
    ),
    _Target(
        "brene_brown", "Brené Brown", "speaker",
        "Warm, story-first, vulnerable.",
        "Conversational warmth, story-first, vulnerability, varied pitch, "
        "relatable asides.",
        wpm=(140, 165), pitch_variability_hz=(40, 90), pauses_per_min=(5, 12),
    ),
    _Target(
        "churchill", "Winston Churchill", "speaker",
        "Slow gravitas and rhythmic builds.",
        "Slow gravitas, long weighty pauses, rhythmic phrasing, rising builds.",
        wpm=(95, 120), pitch_variability_hz=(30, 70), pauses_per_min=(12, 22),
    ),
    _Target(
        "oprah", "Oprah Winfrey", "speaker",
        "Warm, emphatic, direct.",
        "Warm and emphatic, strong emphasis with pitch lift on key words, "
        "direct address, emotional connection.",
        wpm=(135, 160), pitch_variability_hz=(45, 95), pauses_per_min=(6, 14),
    ),
    # --- Style goals (not a person) ---
    _Target(
        "authoritative", "Authoritative", "style",
        "Calm command and conviction.",
        "Slow down, lower and steady, deliberate pauses, declarative endings "
        "(no upspeak), few hedges; project calm command.",
        wpm=(115, 140), pitch_variability_hz=(25, 60), pauses_per_min=(8, 16),
    ),
    _Target(
        "warm", "Warm", "style",
        "Approachable and conversational.",
        "Conversational, smiling tone, varied melodic pitch, inclusive language, "
        "gentle pace.",
        wpm=(135, 160), pitch_variability_hz=(40, 85), pauses_per_min=(5, 12),
    ),
    _Target(
        "energetic", "Energetic", "style",
        "Up-tempo and dynamic.",
        "Up-tempo, dynamic pitch range, punchy emphasis, forward momentum.",
        wpm=(150, 175), pitch_variability_hz=(50, 100), pauses_per_min=(4, 10),
    ),
    _Target(
        "storytelling", "Storytelling", "style",
        "Narrative pacing and color.",
        "Vary pace with the narrative, pause at beats, paint with pitch, build to "
        "a turn.",
        wpm=(130, 155), pitch_variability_hz=(45, 95), pauses_per_min=(8, 16),
    ),
    _Target(
        "executive_presence", "Executive presence", "style",
        "Concise, unhurried, confident.",
        "Concise, unhurried, low and steady, pauses instead of fillers, confident "
        "closings.",
        wpm=(110, 135), pitch_variability_hz=(25, 55), pauses_per_min=(8, 16),
    ),
]

_BY_ID = {t.id: t for t in _TARGETS}


def get(target_id: Optional[str]) -> Optional[_Target]:
    return _BY_ID.get(target_id or "")


def list_targets() -> list[TargetInfo]:
    return [
        TargetInfo(
            id=t.id,
            name=t.name,
            kind=t.kind,
            blurb=t.blurb,
            style_notes=t.style_notes,
            bands=TargetBands(
                wpm=list(t.wpm) if t.wpm else None,
                pitch_variability_hz=list(t.pitch_variability_hz) if t.pitch_variability_hz else None,
                pauses_per_min=list(t.pauses_per_min) if t.pauses_per_min else None,
            ),
        )
        for t in _TARGETS
    ]


def target_bands(target_id: Optional[str]) -> dict:
    """Bands keyed for scoring/comparison; empty when the target isn't steered."""
    t = get(target_id)
    if t is None:
        return {}
    bands = {}
    if t.wpm:
        bands["wpm"] = t.wpm
    if t.pauses_per_min:
        bands["pauses_per_min"] = t.pauses_per_min
    if t.pitch_variability_hz:
        bands["pitch_variability_hz"] = t.pitch_variability_hz
    return bands


def prompt_block(target_id: Optional[str]) -> str:
    """One-line target description for the coaching / delivery-style prompts."""
    t = get(target_id)
    if t is None or t.kind == "balanced":
        return ""
    bands = []
    if t.wpm:
        bands.append(f"pace {int(t.wpm[0])}–{int(t.wpm[1])} wpm")
    if t.pauses_per_min:
        bands.append(f"~{int(t.pauses_per_min[0])}–{int(t.pauses_per_min[1])} pauses/min")
    if t.pitch_variability_hz:
        bands.append(f"pitch variation {int(t.pitch_variability_hz[0])}–{int(t.pitch_variability_hz[1])} Hz")
    band_str = ("; targets: " + ", ".join(bands)) if bands else ""
    label = "speaker to emulate" if t.kind == "speaker" else "delivery goal"
    return f"TARGET ({label}): {t.name} — {t.style_notes}{band_str}"
