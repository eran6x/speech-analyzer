"""OpenAI Audio (text-to-speech) provider.

NOTE: OpenAI TTS does NOT clone the user's voice — it renders the transcript in
a fixed preset voice (alloy, onyx, nova, …). The Claude-authored delivery style
is passed as the `instructions` param for gpt-4o-mini-tts, which honors tone /
pacing direction. Use this for high-quality, style-directed delivery when the
user's own voice isn't required.

Uses `requests` (already a core dep) — no OpenAI SDK needed.
"""

from __future__ import annotations

import os
from typing import Optional

import requests

from .base import TTSProvider

API = "https://api.openai.com/v1/audio/speech"
DEFAULT_MODEL = "gpt-4o-mini-tts"
DEFAULT_VOICE = "alloy"


class OpenAITTS(TTSProvider):
    name = "openai"
    needs_voice_ref = False  # preset voices; no cloning

    def available(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def synthesize(self, text: str, voice_ref_path: Optional[str], style: dict) -> bytes:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        model = style.get("model") or os.getenv("OPENAI_TTS_MODEL", DEFAULT_MODEL)
        voice = style.get("voice") or os.getenv("OPENAI_TTS_VOICE", DEFAULT_VOICE)

        payload = {"model": model, "input": text, "voice": voice, "response_format": "wav"}
        instruction = style.get("instruction")
        if model.startswith("gpt-4o") and instruction:
            # gpt-4o-mini-tts takes free-text delivery direction.
            payload["instructions"] = instruction
        elif style.get("speed"):
            # tts-1 / tts-1-hd take a speed multiplier instead.
            payload["speed"] = max(0.25, min(4.0, float(style["speed"])))

        headers = {"Authorization": f"Bearer {key}", "content-type": "application/json"}
        resp = requests.post(API, headers=headers, json=payload, timeout=120)
        if resp.status_code == 400:
            # Model rejected an optional param — retry with the minimal payload.
            for k in ("instructions", "speed"):
                payload.pop(k, None)
            resp = requests.post(API, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.content  # already WAV
