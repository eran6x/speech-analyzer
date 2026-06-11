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

from .models import Metrics, Scores, Session, Topic

# Current Claude model (see Speech_analyer_plan.md reference docs).
MODEL = "claude-opus-4-8"

SYSTEM = (
    "You are a concise, encouraging speech coach for a sales engineer who "
    "practices presentations and customer conversations daily. You are given "
    "acoustic and transcript metrics plus 1-100 scores for one ~30-60s clip. "
    "Acoustic delivery (pace, pauses, pitch variation, volume, confidence) is "
    "the priority; transcript content (fillers, hedging) is secondary.\n\n"
    "Respond in markdown with exactly these four short sections:\n"
    "**What went well** — one or two specifics, tied to the numbers.\n"
    "**What to fix** — one or two specifics, tied to the lowest scores.\n"
    "**Next time** — one concrete thing to try on the next recording.\n"
    "**Drill** — one targeted exercise for the lowest-scoring dimension.\n\n"
    "Be specific and reference actual metric values. Keep the whole reply under "
    "180 words. Do not invent metrics you weren't given."
)


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


def _build_prompt(topic: Topic, transcript: str, metrics: Metrics,
                  scores: Scores, history: list[Session]) -> str:
    return (
        f"Topic ({topic.category}): {topic.prompt}\n\n"
        f"Scores (1-100): {scores.model_dump(exclude_none=True)}\n"
        f"Metrics: {metrics.model_dump(exclude_none=True)}\n\n"
        f"Recent sessions:\n{_history_summary(history)}\n\n"
        f"Transcript:\n\"\"\"\n{transcript or '(no speech detected)'}\n\"\"\""
    )


def generate_feedback(topic: Topic, transcript: str, metrics: Metrics,
                      scores: Scores, history: list[Session]) -> Optional[str]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None

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
            system=SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": _build_prompt(topic, transcript, metrics, scores, history),
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
