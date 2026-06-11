"""Transcript-based metrics (secondary signal).

Fillers, hedging, and false starts/repetitions are derived from the whisper
transcript. Kept deliberately simple — these are word/phrase counts, easy to
extend as the filler/hedge vocabularies grow.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Standalone filler tokens.
FILLERS = {"um", "uh", "er", "erm", "uhh", "umm", "ah", "hmm", "mm", "mmm"}

# Hedging words and phrases that soften a statement.
HEDGES = [
    "sort of",
    "kind of",
    "i think",
    "i guess",
    "i mean",
    "you know",
    "i suppose",
    "a little",
    "somewhat",
    "maybe",
    "perhaps",
    "probably",
    "just",
]


@dataclass
class TextMetrics:
    word_count: int
    filler_count: int
    filler_density: float  # fillers per 100 words
    hedge_count: int
    false_start_count: int


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _norm(token: str) -> str:
    return re.sub(r"[^a-z']", "", token.lower())


def locate_spans(words) -> tuple[list[tuple[str, float, float]], list[tuple[str, float, float]]]:
    """Map fillers and hedges to (label, start, end) spans using word timestamps.

    `words` are transcription.Word objects (text/start/end), already in order.
    Returns (filler_spans, hedge_spans).
    """
    norm = [(_norm(w.text), w) for w in words]
    tokens = [t for t, _ in norm]

    filler_spans = [(t, w.start, w.end) for t, w in norm if t in FILLERS]

    hedge_spans: list[tuple[str, float, float]] = []
    for phrase in HEDGES:
        parts = phrase.split()
        length = len(parts)
        for i in range(len(tokens) - length + 1):
            if tokens[i : i + length] == parts:
                hedge_spans.append((phrase, norm[i][1].start, norm[i + length - 1][1].end))

    return filler_spans, hedge_spans


def analyze_text(transcript: str) -> TextMetrics:
    tokens = _tokens(transcript)
    word_count = len(tokens)

    filler_count = sum(1 for t in tokens if t in FILLERS)

    lowered = transcript.lower()
    hedge_count = 0
    for phrase in HEDGES:
        hedge_count += len(re.findall(rf"\b{re.escape(phrase)}\b", lowered))

    # False starts / stutters: the same word repeated back-to-back.
    false_start_count = sum(
        1 for prev, curr in zip(tokens, tokens[1:]) if prev == curr
    )

    filler_density = (filler_count / word_count * 100.0) if word_count else 0.0

    return TextMetrics(
        word_count=word_count,
        filler_count=filler_count,
        filler_density=round(filler_density, 1),
        hedge_count=hedge_count,
        false_start_count=false_start_count,
    )
