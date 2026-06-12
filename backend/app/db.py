"""SQLite access layer.

A single file holds every session. The full Session object is stored as JSON in
one column so the schema doesn't need migrating as later phases add metrics; a
few columns are duplicated out for cheap listing/sorting.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from .models import Session

DB_PATH = os.getenv(
    "SPEECH_DB_PATH",
    str(Path(__file__).resolve().parent.parent / "speech_analyzer.db"),
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                timestamp   TEXT NOT NULL,
                data        TEXT NOT NULL
            )
            """
        )


def save_session(session: Session) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, timestamp, data) VALUES (?, ?, ?)",
            (session.id, session.timestamp, session.model_dump_json()),
        )


def list_sessions() -> list[Session]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT data FROM sessions ORDER BY timestamp ASC"
        ).fetchall()
    return [Session.model_validate(json.loads(r["data"])) for r in rows]


def delete_all_sessions() -> int:
    """Delete every session row. Returns the number removed."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM sessions")
        return cur.rowcount


def get_session(session_id: str) -> Session | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT data FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
    if row is None:
        return None
    return Session.model_validate(json.loads(row["data"]))
