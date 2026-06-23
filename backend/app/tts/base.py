"""TTS provider interface.

A `style` dict carries the delivery guidance, e.g.:
    {"instruction": "calm, ~145 wpm, deliberate pauses, no upspeak",
     "target_wpm": 145, "speed": 0.95}
Providers use whatever knobs they support (local engines map `speed`; cloud
engines may also use the natural-language `instruction`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class TTSProvider(ABC):
    name: str = "base"
    # Whether synthesis needs a reference clip of the user's voice (cloning
    # providers do; preset-voice providers like OpenAI don't).
    needs_voice_ref: bool = True

    @abstractmethod
    def available(self) -> bool:
        """True if this provider's dependencies/credentials are present."""

    @abstractmethod
    def synthesize(self, text: str, voice_ref_path: Optional[str], style: dict) -> bytes:
        """Render `text` as WAV bytes, cloning the voice in `voice_ref_path`."""
