"""Text-to-speech provider abstraction.

Pluggable so the engine can be chosen at request time (Settings selector) or via
the TTS_PROVIDER env default — `local` for on-device voice cloning, `elevenlabs`
or `openai` for cloud, or `none` to disable.

Heavy ML dependencies are imported lazily inside each provider, so importing
this package (and the rest of the app) never requires torch / the TTS engine.
"""

from __future__ import annotations

import os
from typing import Optional

from .base import TTSProvider

PROVIDERS = ("local", "elevenlabs", "openai")

_cache: dict[str, Optional[TTSProvider]] = {}


def get_provider(name: Optional[str] = None) -> Optional[TTSProvider]:
    """Return the named provider, or the TTS_PROVIDER env default if name is None.

    Providers are cheap to construct (the local engine only loads its model on
    first synth), so we cache one instance per name.
    """
    name = (name or os.getenv("TTS_PROVIDER", "local")).lower()
    if name in ("cloud",):
        name = "elevenlabs"
    if name in _cache:
        return _cache[name]

    provider: Optional[TTSProvider] = None
    if name == "local":
        from .local import LocalTTS

        provider = LocalTTS()
    elif name == "elevenlabs":
        from .cloud import CloudTTS

        provider = CloudTTS()
    elif name == "openai":
        from .openai_tts import OpenAITTS

        provider = OpenAITTS()

    _cache[name] = provider
    return provider
