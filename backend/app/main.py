"""FastAPI app + routes for the Speech Analyzer.

Phase 1 implements the thinnest end-to-end slice: record -> /analyze ->
transcribe + pace metrics -> persist. The /topic, /sessions, and /sessions/{id}
routes from the API contract are included so the frontend has everything it
needs and later phases just enrich the responses.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import coaching, db, stats
from .acoustic import compute_metrics
from .models import Session, Stats, Topic
from .scoring import compute_scores
from .topics import CATEGORIES, suggest_topic
from .transcription import transcribe

RECORDINGS_DIR = Path(
    os.getenv(
        "RECORDINGS_DIR",
        str(Path(__file__).resolve().parent.parent / "recordings"),
    )
)

app = FastAPI(title="Speech Analyzer", version="0.1.0")

# The Vite dev server runs on a different origin; allow local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/categories", response_model=list[str])
def get_categories() -> list[str]:
    return CATEGORIES


@app.get("/topic", response_model=Topic)
def get_topic(tailored: bool = False, category: str | None = None) -> Topic:
    # When requested, ask the coaching layer for a topic targeting the user's
    # weakest recent dimension; fall back to a random pick if unavailable.
    if tailored:
        topic = coaching.generate_topic(db.list_sessions())
        if topic is not None:
            return topic
    return suggest_topic(category)


@app.post("/analyze", response_model=Session)
async def analyze(
    audio: UploadFile = File(...),
    topic_category: str = Form(...),
    topic_prompt: str = Form(...),
) -> Session:
    session_id = str(uuid.uuid4())

    # Persist the raw upload so we can re-analyze it as metrics evolve.
    suffix = Path(audio.filename or "").suffix or ".webm"
    audio_path = RECORDINGS_DIR / f"{session_id}{suffix}"
    audio_path.write_bytes(await audio.read())

    try:
        transcription = transcribe(str(audio_path))
    except Exception as exc:  # surface a clean error rather than a 500 stack
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")

    metrics, annotations = compute_metrics(transcription, str(audio_path))
    scores = compute_scores(metrics, transcription.duration_sec)

    topic = Topic(category=topic_category, prompt=topic_prompt)
    # Pass recent history (before this session is saved) to the coaching layer.
    feedback = coaching.generate_feedback(
        topic, transcription.text, metrics, scores, db.list_sessions()
    )

    session = Session(
        id=session_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        topic=topic,
        duration_sec=round(transcription.duration_sec, 2),
        transcript=transcription.text,
        metrics=metrics,
        scores=scores,
        feedback=feedback,
        audio_path=str(audio_path),
        annotations=annotations,
    )
    db.save_session(session)
    return session


@app.get("/stats", response_model=Stats)
def get_stats() -> Stats:
    return stats.compute_stats(db.list_sessions())


@app.get("/sessions/{session_id}/audio")
def get_audio(session_id: str) -> FileResponse:
    session = db.get_session(session_id)
    if session is None or not session.audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")
    path = Path(session.audio_path).resolve()
    # Only ever serve files from within the recordings directory.
    recordings_root = RECORDINGS_DIR.resolve()
    if recordings_root not in path.parents or not path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path)


@app.get("/sessions", response_model=list[Session])
def get_sessions() -> list[Session]:
    return db.list_sessions()


@app.get("/sessions/{session_id}", response_model=Session)
def get_session(session_id: str) -> Session:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
