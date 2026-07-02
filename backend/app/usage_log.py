"""Append-only CSV log of voice generations for consumption/cost tracking.

One row per ideal-delivery generation. Open it in any spreadsheet to total
cost, compare providers, and gauge cost-effectiveness over time.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

from . import usage as usage_costs
from .models import GenerationUsage

LOG_PATH = Path(
    os.getenv(
        "VOICE_LOG_PATH",
        str(Path(__file__).resolve().parent.parent / "voice_generations.csv"),
    )
)

COACHING_LOG_PATH = Path(
    os.getenv(
        "COACHING_LOG_PATH",
        str(Path(__file__).resolve().parent.parent / "coaching_usage.csv"),
    )
)

COACHING_FIELDS = [
    "timestamp",
    "session_id",
    "exercise",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "model",
]

FIELDS = [
    "timestamp",
    "session_id",
    "provider",
    "model",
    "style_input_tokens",
    "style_output_tokens",
    "style_cost_usd",
    "tts_characters",
    "tts_audio_seconds",
    "tts_cost_usd",
    "total_cost_usd",
    "estimated",
]


def log(session_id: str, u: GenerationUsage) -> None:
    """Append one generation to the CSV (writing a header on first use)."""
    is_new = not LOG_PATH.exists()
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = u.model_dump()
    row["session_id"] = session_id
    row["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({k: row.get(k) for k in FIELDS})


def log_coaching(session_id: str, exercise: str, usage: dict,
                 model: str = "claude-opus-4-8") -> None:
    """Append one coaching call's token cost to coaching_usage.csv.

    No-op when usage is empty (no key / coaching disabled / call failed).
    """
    if not usage:
        return
    is_new = not COACHING_LOG_PATH.exists()
    COACHING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "exercise": exercise or "single",
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cost_usd": usage_costs.claude_cost(usage),
        "model": model,
    }
    with open(COACHING_LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COACHING_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
