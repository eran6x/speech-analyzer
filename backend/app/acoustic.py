"""Acoustic + combined metric extraction (primary signal).

Pitch and intensity come from parselmouth (Praat); pauses are detected from the
intensity contour. Pace metrics use whisper word timestamps. Phase 2 adds
voice-quality metrics (jitter, shimmer, HNR) and upspeak (rising F0 on
declarative sentence endings). If acoustic analysis fails for any reason, we
fall back to pause detection from word-timestamp gaps so /analyze still returns.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np
import parselmouth
from parselmouth.praat import call

from .audio_io import load_waveform
from .models import Annotation, Metrics
from .text_metrics import analyze_text, locate_spans
from .transcription import Transcription, Word

Span = tuple[float, float]

# A silent stretch longer than this counts as a pause.
PAUSE_THRESHOLD_SEC = 0.25
# Frames quieter than (max_intensity - SILENCE_DROP_DB) are treated as silence.
SILENCE_DROP_DB = 25.0
# Word-gap fallback when acoustic analysis is unavailable.
WORD_GAP_PAUSE_SEC = 0.25

# Pitch search range for voice-quality analysis (typical adult speech).
F0_MIN = 75.0
F0_MAX = 500.0

# Upspeak: F0 rising faster than this over a sentence's final segment.
UPSPEAK_SLOPE_HZ_PER_SEC = 25.0
UPSPEAK_FINAL_SEGMENT_SEC = 0.4


@dataclass
class _Acoustic:
    duration_sec: float
    mean_pitch_hz: float
    pitch_variability: float
    mean_intensity_db: float
    volume_stability: float  # std dev of intensity — lower is steadier
    pause_count: int
    mean_pause_sec: float
    total_pause_sec: float
    pause_spans: list[Span]
    jitter: float | None
    shimmer: float | None
    hnr: float | None
    upspeak_count: int
    upspeak_spans: list[Span]


def _voice_quality(sound: parselmouth.Sound) -> tuple[float | None, float | None, float | None]:
    """Local jitter, local shimmer, and mean HNR (dB). Any may be None."""
    def _clean(x: float) -> float | None:
        return None if x is None or math.isnan(x) else round(float(x), 4)

    jitter = shimmer = hnr = None
    try:
        pp = call(sound, "To PointProcess (periodic, cc)", F0_MIN, F0_MAX)
        jitter = _clean(call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3))
        shimmer = _clean(
            call([sound, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        )
    except Exception:
        pass
    try:
        harmonicity = call(sound, "To Harmonicity (cc)", 0.01, F0_MIN, 0.1, 1.0)
        mean_hnr = call(harmonicity, "Get mean", 0, 0)
        hnr = None if math.isnan(mean_hnr) else round(float(mean_hnr), 1)
    except Exception:
        pass
    return jitter, shimmer, hnr


def _f0_slope(pitch: parselmouth.Pitch, t0: float, t1: float) -> float | None:
    """Linear slope (Hz/sec) of voiced F0 across [t0, t1], or None if too few points."""
    times = np.arange(t0, t1, 0.01)
    pts = []
    for t in times:
        f = pitch.get_value_at_time(float(t))
        if f and not math.isnan(f) and f > 0:
            pts.append((t, f))
    if len(pts) < 3:
        return None
    tt = np.array([p[0] for p in pts])
    ff = np.array([p[1] for p in pts])
    slope, _ = np.polyfit(tt - tt[0], ff, 1)
    return float(slope)


def _compute_upspeak(pitch: parselmouth.Pitch, words: list[Word], text: str) -> list[Span]:
    """Spans of declarative sentences whose final segment rises in pitch.

    Sentences are split on terminal punctuation and aligned to word timestamps
    by token count (words are already in order). Questions are excluded — a
    rising ending there is expected, not upspeak.
    """
    if not words:
        return []
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    idx = 0
    spans: list[Span] = []
    for sentence in sentences:
        tokens = re.findall(r"[a-z']+", sentence.lower())
        n = len(tokens)
        seg = words[idx : idx + n]
        idx += n
        if not seg or sentence.rstrip().endswith("?"):
            continue
        end = seg[-1].end
        final_start = max(seg[0].start, end - UPSPEAK_FINAL_SEGMENT_SEC)
        slope = _f0_slope(pitch, final_start, end)
        if slope is not None and slope > UPSPEAK_SLOPE_HZ_PER_SEC:
            spans.append((final_start, end))
    return spans


def _acoustic_features(audio_path: str, transcription: Transcription) -> _Acoustic:
    samples, sr = load_waveform(audio_path)
    if samples.size == 0:
        raise ValueError("empty audio")

    sound = parselmouth.Sound(samples, sampling_frequency=sr)

    # --- Pitch (F0) over voiced frames ---
    pitch = sound.to_pitch()
    f0 = pitch.selected_array["frequency"]
    voiced = f0[f0 > 0]
    mean_pitch = float(voiced.mean()) if voiced.size else 0.0
    pitch_var = float(voiced.std()) if voiced.size > 1 else 0.0

    # --- Intensity (volume) ---
    intensity = sound.to_intensity()
    values = np.asarray(intensity.values[0], dtype=float)
    values = values[np.isfinite(values)]
    dt = float(intensity.dx)
    t0 = float(intensity.x1)  # time of the first intensity frame

    # --- Pauses: runs of frames below a silence threshold relative to peak ---
    pause_count, total_pause, pause_spans = _detect_pauses(values, dt, t0)
    mean_pause = (total_pause / pause_count) if pause_count else 0.0

    # Volume stats over *sounding* frames only, so silent pauses don't masquerade
    # as low volume or volume instability.
    sounding = values[values >= values.max() - SILENCE_DROP_DB] if values.size else values
    mean_db = float(sounding.mean()) if sounding.size else 0.0
    volume_std = float(sounding.std()) if sounding.size > 1 else 0.0

    jitter, shimmer, hnr = _voice_quality(sound)
    upspeak_spans = _compute_upspeak(pitch, transcription.words, transcription.text)

    return _Acoustic(
        duration_sec=float(sound.get_total_duration()),
        mean_pitch_hz=round(mean_pitch, 1),
        pitch_variability=round(pitch_var, 1),
        mean_intensity_db=round(mean_db, 1),
        volume_stability=round(volume_std, 2),
        pause_count=pause_count,
        mean_pause_sec=round(mean_pause, 2),
        total_pause_sec=total_pause,
        pause_spans=pause_spans,
        jitter=jitter,
        shimmer=shimmer,
        hnr=hnr,
        upspeak_count=len(upspeak_spans),
        upspeak_spans=upspeak_spans,
    )


def _detect_pauses(intensity_db: np.ndarray, dt: float, t0: float) -> tuple[int, float, list[Span]]:
    """Find silent runs longer than PAUSE_THRESHOLD_SEC.

    Returns (count, total_sec, spans) where each span is (start, end) in seconds.
    """
    if intensity_db.size == 0 or dt <= 0:
        return 0, 0.0, []

    threshold = intensity_db.max() - SILENCE_DROP_DB
    silent = intensity_db < threshold
    min_frames = max(1, int(round(PAUSE_THRESHOLD_SEC / dt)))

    total_pause_sec = 0.0
    spans: list[Span] = []
    run = 0
    n = len(silent)
    for i in range(n + 1):
        is_silent = bool(silent[i]) if i < n else False
        if is_silent:
            run += 1
        else:
            if run >= min_frames:
                start = t0 + (i - run) * dt
                end = t0 + i * dt
                spans.append((round(start, 2), round(end, 2)))
                total_pause_sec += run * dt
            run = 0

    return len(spans), round(total_pause_sec, 2), spans


def _word_gap_pauses(transcription: Transcription) -> int:
    return sum(
        1
        for prev, curr in zip(transcription.words, transcription.words[1:])
        if curr.start - prev.end > WORD_GAP_PAUSE_SEC
    )


def _word_annotations(transcription: Transcription) -> list[Annotation]:
    """Filler and hedge spans from the transcript's word timestamps."""
    filler_spans, hedge_spans = locate_spans(transcription.words)
    out = [Annotation(kind="filler", label=lbl, start=round(s, 2), end=round(e, 2)) for lbl, s, e in filler_spans]
    out += [Annotation(kind="hedge", label=lbl, start=round(s, 2), end=round(e, 2)) for lbl, s, e in hedge_spans]
    return out


def compute_metrics(
    transcription: Transcription, audio_path: str
) -> tuple[Metrics, list[Annotation]]:
    words = transcription.words
    word_count = len(words)
    duration = transcription.duration_sec
    wpm = (word_count / duration * 60.0) if duration > 0 else 0.0

    text = analyze_text(transcription.text)
    annotations = _word_annotations(transcription)

    try:
        ac = _acoustic_features(audio_path, transcription)
    except Exception:
        ac = None

    if ac is not None:
        speaking_sec = max(ac.duration_sec - ac.total_pause_sec, 1e-6)
        articulation = word_count / speaking_sec * 60.0
        annotations += [
            Annotation(kind="pause", label="pause", start=s, end=e) for s, e in ac.pause_spans
        ]
        annotations += [
            Annotation(kind="upspeak", label="upspeak", start=round(s, 2), end=round(e, 2))
            for s, e in ac.upspeak_spans
        ]
        annotations.sort(key=lambda a: a.start)
        metrics = Metrics(
            wpm=round(wpm, 1),
            articulation_rate=round(articulation, 1),
            mean_pitch_hz=ac.mean_pitch_hz,
            pitch_variability=ac.pitch_variability,
            mean_intensity_db=ac.mean_intensity_db,
            volume_stability=ac.volume_stability,
            pause_count=ac.pause_count,
            mean_pause_sec=ac.mean_pause_sec,
            filler_count=text.filler_count,
            filler_density=text.filler_density,
            hedge_count=text.hedge_count,
            false_start_count=text.false_start_count,
            upspeak_count=ac.upspeak_count,
            jitter=ac.jitter,
            shimmer=ac.shimmer,
            hnr=ac.hnr,
        )
        return metrics, annotations

    # Fallback: no acoustic features, pauses from word-timestamp gaps.
    annotations.sort(key=lambda a: a.start)
    metrics = Metrics(
        wpm=round(wpm, 1),
        pause_count=_word_gap_pauses(transcription),
        filler_count=text.filler_count,
        filler_density=text.filler_density,
        hedge_count=text.hedge_count,
        false_start_count=text.false_start_count,
    )
    return metrics, annotations
