"""Cloud voice-cloning TTS (ElevenLabs) — for the hosted roadmap.

Stubbed for now: the local provider is the default. When the hosted product
lands, this becomes the real integration (create/lookup a per-account voice from
the enrollment sample, then synthesize), with the API key injected per request
rather than read from a process-global env var.
"""

from __future__ import annotations

import os
from typing import Optional

from .base import TTSProvider


class CloudTTS(TTSProvider):
    name = "elevenlabs"

    def available(self) -> bool:
        return bool(os.getenv("ELEVENLABS_API_KEY"))

    def synthesize(self, text: str, voice_ref_path: Optional[str], style: dict) -> bytes:
        raise NotImplementedError(
            "Cloud TTS (ElevenLabs) is on the hosted roadmap. "
            "Set TTS_PROVIDER=local and install requirements-tts.txt for now."
        )
