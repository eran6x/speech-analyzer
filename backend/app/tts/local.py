"""Local, on-device voice-cloning TTS (default provider).

Uses Coqui XTTS-v2 (via the maintained `coqui-tts` package) for zero-shot voice
cloning from a short reference clip. Requires the optional `requirements-tts.txt`
deps and, realistically, a GPU. All heavy imports are lazy so the rest of the
app runs without these installed.

The reference clip must be a real waveform (WAV) — callers transcode the stored
webm recording first (see audio_io.to_wav_file).
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from .base import TTSProvider

MODEL_NAME = os.getenv("XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
LANGUAGE = os.getenv("TTS_LANGUAGE", "en")


class LocalTTS(TTSProvider):
    name = "local"

    def __init__(self) -> None:
        self._model = None  # lazily loaded, cached for the process
        self.reason: str | None = None  # why unavailable, for diagnostics

    def available(self) -> bool:
        try:
            import torch  # noqa: F401
            import torchcodec  # noqa: F401  (native ffmpeg-backed audio IO)
            from TTS.api import TTS  # noqa: F401

            self.reason = None
            return True
        except Exception as exc:
            self.reason = f"{type(exc).__name__}: {exc}"
            return False

    def _get_model(self):
        # XTTS-v2 ships a non-commercial license prompt that blocks on input()
        # in a server process — auto-accept it (see Phase6_plan.md license note).
        os.environ.setdefault("COQUI_TOS_AGREED", "1")
        if self._model is None:
            import torch
            from TTS.api import TTS

            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = TTS(MODEL_NAME).to(device)
        return self._model

    def synthesize(self, text: str, voice_ref_path: Optional[str], style: dict) -> bytes:
        if not voice_ref_path:
            raise ValueError("Local voice cloning needs a reference clip (enroll a voice or keep recordings).")
        model = self._get_model()
        speed = float(style.get("speed", 1.0))

        out_path = tempfile.mktemp(suffix=".wav")
        kwargs = dict(text=text, speaker_wav=voice_ref_path, language=LANGUAGE, file_path=out_path)
        try:
            try:
                model.tts_to_file(speed=speed, **kwargs)
            except TypeError:
                # Engine/version doesn't accept `speed` — render at default rate.
                model.tts_to_file(**kwargs)
            with open(out_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)
