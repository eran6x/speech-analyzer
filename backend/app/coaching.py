"""Coaching layer — qualitative feedback via the Anthropic Messages API.

After metrics and scores are computed, we send the topic, transcript, metrics,
scores, and a little recent history to Claude and ask for specific, actionable
coaching. The API key comes from ANTHROPIC_API_KEY (.env); if it's absent or the
call fails, we return None and /analyze still succeeds with metrics + scores.
"""

from __future__ import annotations

import json
import os
import re
from statistics import mean
from typing import Optional

from . import profiles
from .models import Metrics, Scores, Session, Topic

# Current Claude model (see Speech_analyer_plan.md reference docs).
MODEL = "claude-opus-4-8"

CRAFT_SYSTEM = (
    "You are an expert speech-delivery coach for a sales engineer. You receive "
    "acoustic + transcript signals for one ~30-60s clip and coach DELIVERY "
    "CRAFT, not metric worship. Cover, where relevant: emphasis and word stress, "
    "vocal variety (pitch and energy), pacing FOR EFFECT, and PAUSES AS A TOOL "
    "— coach where pauses should land (before a key point, after a question), "
    "never just 'use fewer pauses'. Also structure/arc (hook → point → support "
    "→ close), the opening line, the close, and energy/tone. Reference the "
    "signals you're given, but talk about craft. Do NOT default to 'speak "
    "faster' or 'reduce pauses' unless the signals clearly show the speaker is "
    "rushing or stalling and that's the single highest-leverage fix.\n\n"
    "Respond in markdown with these sections:\n"
    "**What landed** — specific delivery strengths.\n"
    "**Sharpen the delivery** — the highest-leverage craft fixes.\n"
    "**Next time** — one concrete thing to try on the next take.\n"
    "**Drill** — one targeted exercise.\n\n"
    "Do not invent signals you weren't given."
)


def _tone_directive(tone: Optional[str]) -> str:
    return {
        "encouraging": "Tone: warm and encouraging; lead with what's working.",
        "blunt": "Tone: direct and blunt; skip pleasantries, be candid about weaknesses.",
    }.get(tone or "", "Tone: balanced and constructive.")


def _depth_directive(depth: Optional[str]) -> str:
    return {
        "brief": "Keep it tight — under ~110 words total.",
        "detailed": "Be thorough — up to ~300 words; a second specific per section is fine.",
    }.get(depth or "", "Keep the whole reply under ~180 words.")


def _signals_summary(annotations) -> str:
    """Compact timing read-out (pause placement, fillers, hedges, upspeak)."""
    if not annotations:
        return "none captured"
    by: dict[str, list] = {}
    for a in annotations:
        by.setdefault(a.kind, []).append(a)
    parts = []
    for kind in ("pause", "filler", "hedge", "upspeak"):
        items = by.get(kind, [])
        if not items:
            continue
        if kind == "pause":
            spans = ", ".join(f"{a.start:.1f}-{a.end:.1f}s" for a in items[:8])
        else:
            spans = ", ".join(f"'{a.label}'@{a.start:.1f}s" for a in items[:8])
        parts.append(f"{kind} ({len(items)}): {spans}")
    return "; ".join(parts) or "clean"


def _open_close(transcript: str) -> tuple[str, str]:
    sents = [s for s in re.split(r"(?<=[.!?])\s+", (transcript or "").strip()) if s]
    if not sents:
        return "", ""
    return sents[0], sents[-1]


def _history_summary(history: list[Session]) -> str:
    recent = history[-3:]
    if not recent:
        return "No prior sessions yet."
    lines = []
    for s in recent:
        lines.append(
            f"- {s.timestamp[:10]} {s.topic.category}: overall={s.scores.overall}, "
            f"pace={s.scores.pace}, pauses={s.scores.pauses}, "
            f"confidence={s.scores.confidence}, fluency={s.scores.fluency}"
        )
    return "\n".join(lines)


def _build_prompt(topic: Topic, transcript: str, metrics: Metrics, scores: Scores,
                  history: list[Session], target: Optional[str], annotations) -> str:
    opening, closing = _open_close(transcript)
    target_block = profiles.prompt_block(target)
    return (
        (f"{target_block}\n\n" if target_block else "")
        + f"Topic ({topic.category}): {topic.prompt}\n\n"
        f"Scores (1-100): {scores.model_dump(exclude_none=True)}\n"
        f"Metrics: {metrics.model_dump(exclude_none=True)}\n"
        f"Timing signals: {_signals_summary(annotations)}\n"
        f"Opening line: \"{opening}\"\n"
        f"Closing line: \"{closing}\"\n\n"
        f"Recent sessions:\n{_history_summary(history)}\n\n"
        f"Transcript:\n\"\"\"\n{transcript or '(no speech detected)'}\n\"\"\""
    )


def generate_feedback(topic: Topic, transcript: str, metrics: Metrics,
                      scores: Scores, history: list[Session],
                      target: Optional[str] = None, tone: Optional[str] = None,
                      depth: Optional[str] = None, annotations=None) -> Optional[str]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None

    system = f"{CRAFT_SYSTEM}\n\n{_tone_directive(tone)} {_depth_directive(depth)}"
    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            thinking={"type": "adaptive"},
            # output_config isn't a typed kwarg in this SDK version; pass it
            # through extra_body so "effort" reaches the API regardless.
            extra_body={"output_config": {"effort": "low"}},  # keep coaching snappy
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": _build_prompt(
                        topic, transcript, metrics, scores, history, target, annotations
                    ),
                }
            ],
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        return text or None
    except Exception:
        # Never let a coaching failure break the analysis loop.
        return None


# --- Tailored topic generation (Phase 2) ---

_SCORE_DIMS = ("pace", "pauses", "confidence", "fluency")

TOPIC_SYSTEM = (
    "You are a speech coach for a sales engineer who practices presentations and "
    "customer conversations. Suggest ONE short speaking-practice topic chosen to "
    "push them to improve a specific weak delivery dimension.\n\n"
    "Respond with ONLY a JSON object, no other text:\n"
    '{"category": <one of: small talk, presentation, job interview, '
    'promotion pitch, custom>, "prompt": <one sentence, a concrete speaking '
    "prompt that yields 30-60 seconds of speech>}"
)


def _weakest_dimension(history: list[Session]) -> Optional[str]:
    recent = history[-5:]
    if not recent:
        return None
    averages: dict[str, float] = {}
    for dim in _SCORE_DIMS:
        vals = [getattr(s.scores, dim) for s in recent if getattr(s.scores, dim) is not None]
        if vals:
            averages[dim] = mean(vals)
    if not averages:
        return None
    return min(averages, key=averages.get)


def _parse_topic(text: str) -> Optional[Topic]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return Topic(category=str(data["category"]), prompt=str(data["prompt"]))
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def generate_topic(history: list[Session]) -> Optional[Topic]:
    """Suggest a topic targeting the user's weakest recent dimension.

    Returns None (caller falls back to a random topic) when there's no API key,
    no scored history to learn from, or the call/parse fails.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    weakest = _weakest_dimension(history)
    if weakest is None:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            thinking={"type": "adaptive"},
            extra_body={"output_config": {"effort": "low"}},
            system=TOPIC_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"My weakest delivery dimension lately is {weakest}. "
                        f"Suggest a practice topic that will specifically push me "
                        f"to improve {weakest}."
                    ),
                }
            ],
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        return _parse_topic(text)
    except Exception:
        return None


# --- Delivery-style guidance for the "ideal delivery" audio (Phase 6) ---

# Center of the ideal pace band (kept in sync with scoring.CONFIG["pace"]).
_IDEAL_WPM = 145

DELIVERY_SYSTEM = (
    "You are a speech-delivery director. Given a transcript and its delivery "
    "metrics/scores, write a ONE-sentence instruction for how the SAME words "
    "should ideally be delivered to fix the weak areas — pace, pauses, pitch "
    "variation, projection, no upspeak, no fillers/hedging. Be concrete and "
    "vocal-direction style (e.g. 'Calm and confident at ~145 wpm, with a "
    "deliberate beat at each sentence break and lift on key words; statements "
    "land flat'). Output ONLY that sentence — no preamble, under 40 words."
)


def _fallback_delivery_style(metrics: Metrics) -> str:
    bits = [f"Speak at a steady ~{_IDEAL_WPM} words per minute"]
    if metrics.pause_count is not None and metrics.pause_count <= 1:
        bits.append("add deliberate pauses at sentence boundaries")
    if metrics.pitch_variability is not None and metrics.pitch_variability < 20:
        bits.append("vary your pitch on key words instead of staying flat")
    if metrics.upspeak_count:
        bits.append("end statements on a falling tone, not rising")
    if metrics.filler_count or metrics.hedge_count:
        bits.append("drop fillers and hedging")
    bits.append("sound calm and confident")
    return ", ".join(bits) + "."


def generate_delivery_style(
    transcript: str, metrics: Metrics, scores: Scores, target: Optional[str] = None
) -> tuple[str, Optional[dict]]:
    """Short vocal-direction instruction for the ideal delivery.

    Returns (instruction, usage) where usage is the Claude token counts
    ({"input_tokens", "output_tokens"}) or None when the metric-derived fallback
    is used (no API key / call failed), so audio generation works offline.
    When a target is set, the instruction emulates that style.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return _fallback_delivery_style(metrics), None
    target_block = profiles.prompt_block(target)
    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            extra_body={"output_config": {"effort": "low"}},
            system=DELIVERY_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        (f"{target_block}\n" if target_block else "")
                        + f"Scores: {scores.model_dump(exclude_none=True)}\n"
                        f"Metrics: {metrics.model_dump(exclude_none=True)}\n"
                        f"Transcript:\n{transcript}"
                    ),
                }
            ],
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        if not text:
            return _fallback_delivery_style(metrics), None
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return text, usage
    except Exception:
        return _fallback_delivery_style(metrics), None
