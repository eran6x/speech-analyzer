"""Audio decoding.

MediaRecorder produces webm/opus, which Praat/parselmouth can't read directly.
PyAV (a faster-whisper dependency, so already installed) decodes essentially any
container into a mono float32 waveform we can hand to parselmouth.
"""

from __future__ import annotations

import av
import numpy as np

TARGET_SR = 16000


def load_waveform(path: str, target_sr: int = TARGET_SR) -> tuple[np.ndarray, int]:
    """Decode an audio file to a mono float32 array in [-1, 1] at target_sr."""
    container = av.open(path)
    try:
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="s16", layout="mono", rate=target_sr)
        chunks: list[np.ndarray] = []
        for frame in container.decode(stream):
            for resampled in resampler.resample(frame):
                # s16 mono frames come back shaped (1, n_samples)
                chunks.append(resampled.to_ndarray().reshape(-1))
    finally:
        container.close()

    if not chunks:
        return np.zeros(0, dtype=np.float32), target_sr

    samples = np.concatenate(chunks).astype(np.float32) / 32768.0
    return samples, target_sr
