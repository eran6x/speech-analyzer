"""Per-generation token/cost accounting for ideal-delivery synthesis.

Claude (delivery-style) tokens are exact. TTS cost is an estimate — OpenAI's
speech endpoint returns no usage, so we derive it from input characters + audio
length. All rates are env-overridable (USD).
"""

from __future__ import annotations

import math
import os
from typing import Optional

from .models import GenerationUsage


def _rate(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# Claude delivery-style LLM (defaults: Opus 4.8 per-MTok).
CLAUDE_IN = _rate("CLAUDE_USD_PER_MTOK_INPUT", 5.0)
CLAUDE_OUT = _rate("CLAUDE_USD_PER_MTOK_OUTPUT", 25.0)
# OpenAI TTS: gpt-4o-mini-tts (audio per-minute + text-token input),
# and tts-1 / tts-1-hd (per-character).
OPENAI_TTS_PER_MIN = _rate("OPENAI_TTS_USD_PER_MIN", 0.015)
OPENAI_TTS_IN = _rate("OPENAI_TTS_USD_PER_MTOK_INPUT", 0.60)
OPENAI_TTS1_PER_MCHAR = _rate("OPENAI_TTS1_USD_PER_MCHAR", 15.0)


def _round(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x, 6)


def claude_cost(usage: Optional[dict]) -> Optional[float]:
    """USD cost of a Claude call from its token usage (or None)."""
    if not usage:
        return None
    return _round(
        usage.get("input_tokens", 0) / 1e6 * CLAUDE_IN
        + usage.get("output_tokens", 0) / 1e6 * CLAUDE_OUT
    )


# Back-compat alias used by the ideal-delivery usage builder.
_style_cost = claude_cost


def _tts_cost(provider: str, model: Optional[str], chars: int, seconds: float) -> Optional[float]:
    if provider == "local":
        return 0.0  # on-device
    if provider == "openai":
        m = model or ""
        if m.startswith("gpt-4o"):
            input_tokens = math.ceil(chars / 4)
            return _round(input_tokens / 1e6 * OPENAI_TTS_IN + seconds / 60.0 * OPENAI_TTS_PER_MIN)
        if m.startswith("tts-1"):
            mult = 2.0 if "hd" in m else 1.0
            return _round(chars / 1e6 * OPENAI_TTS1_PER_MCHAR * mult)
    return None  # ElevenLabs / unknown: plan-dependent


def build(provider: str, model: Optional[str], transcript: str,
          style_usage: Optional[dict], audio_seconds: float) -> GenerationUsage:
    chars = len(transcript or "")
    style_cost = _style_cost(style_usage)
    tts_cost = _tts_cost(provider, model, chars, audio_seconds or 0.0)
    parts = [c for c in (style_cost, tts_cost) if c is not None]
    total = _round(sum(parts)) if parts else None
    return GenerationUsage(
        provider=provider,
        model=model,
        style_input_tokens=(style_usage or {}).get("input_tokens"),
        style_output_tokens=(style_usage or {}).get("output_tokens"),
        style_cost_usd=style_cost,
        tts_characters=chars,
        tts_audio_seconds=round(audio_seconds or 0.0, 1),
        tts_cost_usd=tts_cost,
        total_cost_usd=total,
    )
