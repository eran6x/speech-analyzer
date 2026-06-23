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


def write_wav(samples: np.ndarray, sr: int, dst_path: str) -> None:
    """Write a float32 [-1, 1] mono array as a 16-bit PCM WAV."""
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(dst_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# Silence-trim tuning.
TRIM_STORE_SR = 48000   # preserve fidelity (opus is 48k); analysis downsamples
LEAD_KEEP_SEC = 0.10    # keep a short run-in before the first speech
TAIL_KEEP_SEC = 0.10    # keep a short tail after the last speech
MIN_TRIM_SEC = 0.20     # only trim an end if its silence exceeds this


def _speech_bounds(samples: np.ndarray, sr: int) -> tuple[int, int]:
    """(first, last+1) sample indices of speech, via short-time RMS threshold."""
    win = max(1, int(0.02 * sr))  # 20 ms frames
    nf = len(samples) // win
    if nf == 0:
        return 0, len(samples)
    frames = samples[: nf * win].reshape(nf, win)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    peak = float(rms.max()) if rms.size else 0.0
    threshold = max(peak * 0.10, 1e-3)  # 10% of peak, with a noise floor
    voiced = np.where(rms > threshold)[0]
    if voiced.size == 0:
        return 0, len(samples)
    start = int(voiced[0] * win)
    end = int(min(len(samples), (voiced[-1] + 1) * win))
    return start, end


def trim_silence(src_path: str, dst_path: str,
                 store_sr: int = TRIM_STORE_SR) -> tuple[str, float, float]:
    """Trim silence before the first and after the last speech.

    Returns (path_to_use, lead_trimmed_sec, tail_trimmed_sec). Writes a trimmed
    WAV to dst_path when either end has meaningful silence; otherwise returns the
    original src_path unchanged.
    """
    samples, sr = load_waveform(src_path, store_sr)
    n = samples.size
    if n == 0:
        return src_path, 0.0, 0.0
    start, end = _speech_bounds(samples, sr)
    new_start = max(0, start - int(LEAD_KEEP_SEC * sr))
    new_end = min(n, end + int(TAIL_KEEP_SEC * sr))
    lead_trim = new_start / sr
    tail_trim = (n - new_end) / sr
    if lead_trim < MIN_TRIM_SEC and tail_trim < MIN_TRIM_SEC:
        return src_path, 0.0, 0.0
    write_wav(samples[new_start:new_end], sr, dst_path)
    return dst_path, round(lead_trim, 2), round(tail_trim, 2)
