"""Text-to-speech provider abstraction.

Pluggable so the engine can be swapped via the TTS_PROVIDER env var without
touching callers — `local` (default) for on-device voice cloning, `elevenlabs`
for the hosted/cloud roadmap, or `none` to disable the feature.

Heavy ML dependencies are imported lazily inside the provider, so importing this
package (and the rest of the app) never requires torch / the TTS engine.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from .base import TTSProvider


@lru_cache(maxsize=1)
def get_provider() -> Optional[TTSProvider]:
    name = os.getenv("TTS_PROVIDER", "local").lower()
    if name == "local":
        from .local import LocalTTS

        return LocalTTS()
    if name in ("elevenlabs", "cloud"):
        from .cloud import CloudTTS

        return CloudTTS()
    return None
