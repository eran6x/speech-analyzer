"""faster-whisper wrapper.

Returns the transcript plus word-level timestamps, which downstream metrics
(pace, pauses) depend on. The model is loaded lazily and cached so the heavy
load cost is paid once per process.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from faster_whisper import WhisperModel

# "base" is a good speed/accuracy trade-off for short local clips. Override via
# env without touching code.
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
# CPU + int8 keeps this runnable on a laptop without a GPU.
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Transcription:
    text: str
    words: list[Word]
    duration_sec: float


@lru_cache(maxsize=1)
def _get_model() -> WhisperModel:
    return WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)


def transcribe(audio_path: str) -> Transcription:
    """Transcribe an audio file and return text + word timestamps + duration."""
    model = _get_model()
    segments, info = model.transcribe(audio_path, word_timestamps=True)

    words: list[Word] = []
    text_parts: list[str] = []
    for segment in segments:
        text_parts.append(segment.text)
        for w in segment.words or []:
            words.append(Word(text=w.word.strip(), start=w.start, end=w.end))

    # Prefer measured speech span; fall back to whisper's duration estimate.
    if words:
        duration = words[-1].end - words[0].start
    else:
        duration = float(getattr(info, "duration", 0.0))

    return Transcription(
        text=" ".join(p.strip() for p in text_parts).strip(),
        words=words,
        duration_sec=max(duration, 0.0),
    )
