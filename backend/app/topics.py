"""Topic library and suggestion logic.

Phase 1: a static list with a random pick. Later phases may tailor topics to
the user's weakest dimension (see roadmap Phase 2).
"""

from __future__ import annotations

import random
from typing import Optional

from .models import Topic

TOPICS: list[Topic] = [
    Topic(
        category="small talk",
        prompt="Introduce yourself to a new colleague at a conference and ask about their work.",
    ),
    Topic(
        category="presentation",
        prompt="Give the 60-second opening of a product demo: hook the audience and set up the problem.",
    ),
    Topic(
        category="job interview",
        prompt="Answer: 'Tell me about a time you turned a skeptical customer into an advocate.'",
    ),
    Topic(
        category="promotion pitch",
        prompt="Make the case to your manager for why you're ready for the next level.",
    ),
    Topic(
        category="custom",
        prompt="Explain a technical concept from your product to a non-technical buyer.",
    ),
]


CATEGORIES = [t.category for t in TOPICS]


def suggest_topic(category: Optional[str] = None) -> Topic:
    """Return a random topic, optionally restricted to a single category."""
    if category:
        matches = [t for t in TOPICS if t.category == category]
        if matches:
            return random.choice(matches)
    return random.choice(TOPICS)
