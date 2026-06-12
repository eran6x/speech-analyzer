"""FastAPI app + routes for the Speech Analyzer.

Phase 1 implements the thinnest end-to-end slice: record -> /analyze ->
transcribe + pace metrics -> persist. The /topic, /sessions, and /sessions/{id}
routes from the API contract are included so the frontend has everything it
needs and later phases just enrich the responses.
"""

from __future__ import annotations

import io
import os
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import coaching, db, stats
from .acoustic import compute_metrics
from .audio_io import load_waveform
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

# The Vite dev server runs on a different origin (and may fall back to another
# port if 5173 is taken); allow any localhost port during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
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
    enable_coaching: bool = Form(True),
    keep_recording: bool = Form(True),
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
    # Coaching is opt-out via Settings; pass recent history for context.
    feedback = (
        coaching.generate_feedback(
            topic, transcription.text, metrics, scores, db.list_sessions()
        )
        if enable_coaching
        else None
    )

    # Privacy: when "keep recordings" is off, discard the audio after analysis
    # (metrics/transcript are already computed). Playback won't be available.
    if keep_recording:
        saved_audio_path = str(audio_path)
    else:
        audio_path.unlink(missing_ok=True)
        saved_audio_path = None

    session = Session(
        id=session_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        topic=topic,
        duration_sec=round(transcription.duration_sec, 2),
        transcript=transcription.text,
        metrics=metrics,
        scores=scores,
        feedback=feedback,
        audio_path=saved_audio_path,
        annotations=annotations,
    )
    db.save_session(session)
    return session


@app.delete("/sessions")
def delete_sessions() -> dict:
    """Delete all sessions and remove stored recordings (privacy)."""
    deleted = db.delete_all_sessions()
    for f in RECORDINGS_DIR.glob("*"):
        if f.is_file():
            f.unlink(missing_ok=True)
    return {"deleted": deleted}


@app.get("/stats", response_model=Stats)
def get_stats() -> Stats:
    return stats.compute_stats(db.list_sessions())


@app.get("/sessions/{session_id}/audio")
def get_audio(session_id: str) -> Response:
    session = db.get_session(session_id)
    if session is None or not session.audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")
    path = Path(session.audio_path).resolve()
    # Only ever serve files from within the recordings directory.
    recordings_root = RECORDINGS_DIR.resolve()
    if recordings_root not in path.parents or not path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    # Transcode to WAV so every browser can decode it for playback + waveform
    # (MediaRecorder webm/opus isn't reliably decodable via WebAudio).
    try:
        samples, sr = load_waveform(str(path))
    except Exception:
        raise HTTPException(status_code=500, detail="Could not decode audio")
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return Response(content=buf.getvalue(), media_type="audio/wav")


@app.get("/sessions", response_model=list[Session])
def get_sessions() -> list[Session]:
    return db.list_sessions()


@app.get("/sessions/{session_id}", response_model=Session)
def get_session(session_id: str) -> Session:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
