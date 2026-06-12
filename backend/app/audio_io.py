"""Audio decoding.

MediaRecorder produces webm/opus, which Praat/parselmouth can't read directly.
PyAV (a faster-whisper dependency, so already installed) decodes essentially any
container into a mono float32 waveform we can hand to parselmouth.
"""

from __future__ import annotations

import io
import wave

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


def to_wav_bytes(src_path: str, target_sr: int = TARGET_SR) -> bytes:
    """Decode any supported audio file to mono 16-bit WAV bytes."""
    samples, sr = load_waveform(src_path, target_sr)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def to_wav_file(src_path: str, dst_path: str, target_sr: int = TARGET_SR) -> None:
    """Decode any supported audio file and write it as a mono 16-bit WAV."""
    with open(dst_path, "wb") as f:
        f.write(to_wav_bytes(src_path, target_sr))
