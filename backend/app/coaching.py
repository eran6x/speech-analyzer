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
    "Respond in PLAIN TEXT — no markdown, no asterisks, no bullet characters, "
    "no '#'. Use exactly these four section headings, each on its own line and "
    "verbatim, followed by 1-2 short sentences, with a blank line between "
    "sections:\n"
    "What landed\n"
    "Sharpen the delivery\n"
    "Next time\n"
    "Drill\n\n"
    "Content: What landed = specific delivery strengths; Sharpen the delivery = "
    "the highest-leverage craft fixes; Next time = one concrete thing to try; "
    "Drill = one targeted exercise. Do not invent signals you weren't given."
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


def _conversation_block(conversation) -> str:
    if not conversation:
        return ""
    lines = ["Conversation drill — questions asked and the user's answers:"]
    for i, t in enumerate(conversation, 1):
        q = t.question if hasattr(t, "question") else t.get("question", "")
        a = t.answer if hasattr(t, "answer") else t.get("answer", "")
        lines.append(f"{i}. Q: {q}\n   A: {a or '(no answer captured)'}")
    return "\n".join(lines)


def _build_prompt(topic: Topic, transcript: str, metrics: Metrics, scores: Scores,
                  history: list[Session], target: Optional[str], annotations,
                  conversation=None) -> str:
    opening, closing = _open_close(transcript)
    target_block = profiles.prompt_block(target)
    convo = _conversation_block(conversation)
    return (
        (f"{target_block}\n\n" if target_block else "")
        + (f"{convo}\n\n" if convo else "")
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
                      depth: Optional[str] = None, annotations=None,
                      conversation=None) -> tuple[Optional[str], Optional[dict]]:
    """Returns (feedback, usage). usage is Claude token counts, or None when the
    call didn't happen (no key / disabled) or failed."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None, None

    convo_directive = (
        " This was a rapid conversation drill: the user answered a series of "
        "questions on the spot. Also assess responsiveness, how well each answer "
        "actually addressed its question, and thinking on their feet — alongside "
        "the usual delivery craft."
        if conversation
        else ""
    )
    system = (
        f"{CRAFT_SYSTEM}{convo_directive}\n\n"
        f"{_tone_directive(tone)} {_depth_directive(depth)}"
    )
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
                        topic, transcript, metrics, scores, history, target,
                        annotations, conversation,
                    ),
                }
            ],
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        if not text:
            return None, None
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return text, usage
    except Exception:
        # Never let a coaching failure break the analysis loop.
        return None, None


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


# --- Conversation drill question generation (Phase 9) ---

CONVERSATION_SYSTEM = (
    "You are an interviewer running a rapid, friendly 'think on your feet' "
    "conversation drill. Given a theme and a count N, write exactly N short "
    "spoken questions that ESCALATE: start with an easy icebreaker, then dig "
    "deeper with follow-ups, and end with a 'deepener' that asks for an opinion, "
    "recommendation, or reflection. Each question is one natural sentence, "
    "standalone, and answerable in ~15-30 seconds. Output ONLY a JSON array of "
    "N strings — no numbering, no extra text."
)

# Offline fallback when there's no API key — generic escalating questions per
# theme (sliced to N; extras reused generically).
_QUESTION_BANK = {
    "small talk": [
        "Do you have any fun plans lined up for the weekend?",
        "Is that something you get to do often, or has it been on your list a while?",
        "For someone who's never tried it, what's the one must-know tip?",
        "What first got you into it?",
        "Who would you most want to do that with, and why?",
    ],
    "presentation": [
        "In one sentence, what's the big idea you want your audience to remember?",
        "Why should they care about this right now?",
        "What's the strongest proof point you'd lead with?",
        "What objection do you expect, and how would you answer it?",
        "How would you close so it sticks?",
    ],
    "job interview": [
        "Tell me a bit about yourself and what you're looking for.",
        "Walk me through a project you're genuinely proud of.",
        "What was the hardest part of that, and how did you handle it?",
        "Where do you want to grow next?",
        "Why this role, and why now?",
    ],
    "promotion pitch": [
        "What impact have you had that you're proudest of this year?",
        "How has your scope grown beyond your current level?",
        "Tell me about a time you led without being asked to.",
        "What would you take on at the next level?",
        "Why are you ready for it now?",
    ],
    "custom": [
        "Tell me about the topic you want to practice.",
        "What's the most important point you'd make?",
        "Why does it matter, and to whom?",
        "What's a common misconception about it?",
        "If you had one line to persuade someone, what would it be?",
    ],
}


def _fallback_questions(theme: str, n: int) -> list[str]:
    bank = _QUESTION_BANK.get(theme, _QUESTION_BANK["custom"])
    if n <= len(bank):
        return bank[:n]
    # Pad by cycling if more are requested than the bank holds.
    return [bank[i % len(bank)] for i in range(n)]


def _parse_questions(text: str, n: int) -> Optional[list[str]]:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    items = [str(q).strip() for q in data if str(q).strip()]
    return items[:n] if items else None


def generate_conversation_questions(theme: str, n: int = 3) -> list[str]:
    """N escalating questions on a theme, generated up front.

    Generic on a free-text theme. Always returns usable questions: a static
    per-theme fallback when there's no API key or the call/parse fails.
    """
    n = max(1, min(n, 8))
    if not os.getenv("ANTHROPIC_API_KEY"):
        return _fallback_questions(theme, n)
    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            extra_body={"output_config": {"effort": "low"}},
            system=CONVERSATION_SYSTEM,
            messages=[{"role": "user", "content": f"Theme: {theme}\nN: {n}"}],
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        return _parse_questions(text, n) or _fallback_questions(theme, n)
    except Exception:
        return _fallback_questions(theme, n)


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
