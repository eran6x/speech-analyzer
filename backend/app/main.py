"""FastAPI app + routes for the Speech Analyzer.

Phase 1 implements the thinnest end-to-end slice: record -> /analyze ->
transcribe + pace metrics -> persist. The /topic, /sessions, and /sessions/{id}
routes from the API contract are included so the frontend has everything it
needs and later phases just enrich the responses.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import coaching, db, stats, tts
from .acoustic import compute_metrics
from .audio_io import to_wav_bytes, to_wav_file
from .models import Session, Stats, Topic
from .scoring import CONFIG as SCORING_CONFIG, compute_scores
from .topics import CATEGORIES, suggest_topic
from .transcription import transcribe

RECORDINGS_DIR = Path(
    os.getenv(
        "RECORDINGS_DIR",
        str(Path(__file__).resolve().parent.parent / "recordings"),
    )
)
# Single-user voice enrollment sample (becomes per-account in the hosted product).
VOICE_DIR = RECORDINGS_DIR / "voice"
ENROLLMENT_PATH = VOICE_DIR / "enrollment.wav"

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
    VOICE_DIR.mkdir(parents=True, exist_ok=True)


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
    if not _within_recordings(path):
        raise HTTPException(status_code=404, detail="Audio not found")
    # Transcode to WAV so every browser can decode it for playback + waveform
    # (MediaRecorder webm/opus isn't reliably decodable via WebAudio).
    try:
        return Response(content=to_wav_bytes(str(path)), media_type="audio/wav")
    except Exception:
        raise HTTPException(status_code=500, detail="Could not decode audio")


def _within_recordings(path: Path) -> bool:
    """Path-traversal guard: the file must live under RECORDINGS_DIR and exist."""
    return RECORDINGS_DIR.resolve() in path.parents and path.exists()


def _resolve_voice_ref(session: Session) -> tuple[str | None, bool]:
    """Return (wav_path, is_temp) for cloning: enrollment if present, else the
    session's own recording transcoded to a temp WAV. (None, False) if neither."""
    if ENROLLMENT_PATH.exists():
        return str(ENROLLMENT_PATH), False
    if session.audio_path:
        src = Path(session.audio_path).resolve()
        if _within_recordings(src):
            tmp = tempfile.mktemp(suffix=".wav")
            to_wav_file(str(src), tmp)
            return tmp, True
    return None, False


@app.post("/voice")
async def set_voice(audio: UploadFile = File(...)) -> dict:
    """Save a voice-enrollment sample (transcoded to WAV) for cloning."""
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(audio.filename or "").suffix or ".webm"
    tmp = VOICE_DIR / f"upload{suffix}"
    tmp.write_bytes(await audio.read())
    try:
        to_wav_file(str(tmp), str(ENROLLMENT_PATH))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not process voice sample")
    finally:
        tmp.unlink(missing_ok=True)
    return {"enrolled": True}


@app.get("/voice")
def get_voice() -> dict:
    return {"enrolled": ENROLLMENT_PATH.exists()}


@app.delete("/voice")
def delete_voice() -> dict:
    ENROLLMENT_PATH.unlink(missing_ok=True)
    return {"enrolled": False}


@app.post("/sessions/{session_id}/ideal", response_model=Session)
def generate_ideal(session_id: str) -> Session:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.transcript.strip():
        raise HTTPException(status_code=400, detail="No transcript to synthesize")

    provider = tts.get_provider()
    if provider is None or not provider.available():
        detail = "Voice TTS engine unavailable. Install requirements-tts.txt and set TTS_PROVIDER=local."
        reason = getattr(provider, "reason", None)
        if reason:
            detail += f" ({reason})"
        raise HTTPException(status_code=503, detail=detail)

    ref_path, is_temp = _resolve_voice_ref(session)
    if ref_path is None:
        raise HTTPException(
            status_code=400,
            detail="No voice reference: enroll a voice sample in Settings, or enable 'keep recordings'.",
        )

    try:
        style_text = coaching.generate_delivery_style(
            session.transcript, session.metrics, session.scores
        )
        pace = SCORING_CONFIG["pace"]
        target_wpm = (pace["ideal_min"] + pace["ideal_max"]) / 2
        user_wpm = session.metrics.wpm or target_wpm
        speed = max(0.7, min(1.3, target_wpm / user_wpm)) if user_wpm > 0 else 1.0
        wav = provider.synthesize(
            session.transcript,
            ref_path,
            {"instruction": style_text, "target_wpm": target_wpm, "speed": round(speed, 3)},
        )
    except HTTPException:
        raise
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}")
    finally:
        if is_temp and ref_path and os.path.exists(ref_path):
            os.remove(ref_path)

    ideal_path = RECORDINGS_DIR / f"{session_id}_ideal.wav"
    ideal_path.write_bytes(wav)
    session.ideal_audio_path = str(ideal_path)
    session.delivery_style = style_text
    db.save_session(session)
    return session


@app.get("/sessions/{session_id}/ideal/audio")
def get_ideal_audio(session_id: str) -> Response:
    session = db.get_session(session_id)
    if session is None or not session.ideal_audio_path:
        raise HTTPException(status_code=404, detail="Ideal audio not found")
    path = Path(session.ideal_audio_path).resolve()
    if not _within_recordings(path):
        raise HTTPException(status_code=404, detail="Ideal audio not found")
    return Response(content=path.read_bytes(), media_type="audio/wav")


@app.get("/sessions", response_model=list[Session])
def get_sessions() -> list[Session]:
    return db.list_sessions()


@app.get("/sessions/{session_id}", response_model=Session)
def get_session(session_id: str) -> Session:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
