"""Cloud voice-cloning TTS via ElevenLabs.

Higher fidelity than the local engine. Enable with TTS_PROVIDER=elevenlabs and
ELEVENLABS_API_KEY. If ELEVENLABS_VOICE_ID is set it's used directly; otherwise
an instant voice is cloned from the reference clip for the request and deleted
afterward.

NOTE: implemented against the ElevenLabs HTTP API but not exercised in CI (no
key here). In the hosted product the key becomes a per-account credential
injected per request rather than a process env var (see Phase6_plan.md roadmap).
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional

import requests

from ..audio_io import to_wav_bytes
from .base import TTSProvider

API = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL = "eleven_multilingual_v2"


class CloudTTS(TTSProvider):
    name = "elevenlabs"

    def available(self) -> bool:
        return bool(os.getenv("ELEVENLABS_API_KEY"))

    def _headers(self) -> dict:
        return {"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}

    def synthesize(self, text: str, voice_ref_path: Optional[str], style: dict) -> bytes:
        if not os.getenv("ELEVENLABS_API_KEY"):
            raise RuntimeError("ELEVENLABS_API_KEY is not set.")
        model_id = os.getenv("ELEVENLABS_MODEL", DEFAULT_MODEL)
        voice_id = os.getenv("ELEVENLABS_VOICE_ID")
        created = False

        try:
            if not voice_id:
                if not voice_ref_path:
                    raise ValueError("A voice reference is required to clone a voice.")
                voice_id = self._create_voice(voice_ref_path)
                created = True
            mp3 = self._tts(voice_id, text, model_id, style)
        finally:
            if created and voice_id:
                self._delete_voice(voice_id)

        # ElevenLabs returns mp3; transcode to WAV for our uniform pipeline.
        tmp = tempfile.mktemp(suffix=".mp3")
        try:
            with open(tmp, "wb") as f:
                f.write(mp3)
            return to_wav_bytes(tmp)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def _create_voice(self, ref_path: str) -> str:
        with open(ref_path, "rb") as f:
            resp = requests.post(
                f"{API}/voices/add",
                headers=self._headers(),
                data={"name": "speech-analyzer-ideal", "description": "temporary clone"},
                files={"files": ("reference.wav", f, "audio/wav")},
                timeout=120,
            )
        resp.raise_for_status()
        return resp.json()["voice_id"]

    def _tts(self, voice_id: str, text: str, model_id: str, style: dict) -> bytes:
        speed = max(0.7, min(1.2, float(style.get("speed", 1.0))))
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.8,
                "style": 0.3,
                "use_speaker_boost": True,
                "speed": speed,
            },
        }
        url = f"{API}/text-to-speech/{voice_id}"
        headers = {**self._headers(), "accept": "audio/mpeg", "content-type": "application/json"}
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 422:
            # Some models reject `speed` in voice_settings — retry without it.
            payload["voice_settings"].pop("speed", None)
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.content

    def _delete_voice(self, voice_id: str) -> None:
        try:
            requests.delete(f"{API}/voices/{voice_id}", headers=self._headers(), timeout=30)
        except Exception:
            pass
