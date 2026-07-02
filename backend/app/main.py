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

from . import coaching, db, profiles, stats, tts, usage, usage_log
from .acoustic import compute_metrics
from .audio_io import load_waveform, to_wav_bytes, to_wav_file, trim_silence
from .models import Session, Stats, TargetInfo, Topic, TranscriptUpdate
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
# Voice-clone references use a higher sample rate than the 16 kHz analysis path —
# 16 kHz references make XTTS sound metallic.
CLONE_SR = int(os.getenv("CLONE_SR", "24000"))

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
    coaching_target: str = Form(""),
    coaching_tone: str = Form(""),
    coaching_depth: str = Form(""),
    parent_id: str = Form(""),
) -> Session:
    session_id = str(uuid.uuid4())

    suffix = Path(audio.filename or "").suffix or ".webm"
    raw_path = RECORDINGS_DIR / f"{session_id}{suffix}"
    raw_path.write_bytes(await audio.read())

    # Trim silence before/after the user speaks so it isn't evaluated
    # (otherwise it inflates pause count and lowers articulation). The trimmed
    # WAV is used for both transcription and acoustic analysis.
    try:
        trimmed, _, _ = trim_silence(str(raw_path), str(RECORDINGS_DIR / f"{session_id}.wav"))
    except Exception:
        trimmed = str(raw_path)
    audio_path = Path(trimmed)
    if audio_path != raw_path:  # a distinct trimmed file replaced the upload
        raw_path.unlink(missing_ok=True)

    try:
        transcription = transcribe(str(audio_path))
    except Exception as exc:  # surface a clean error rather than a 500 stack
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")

    metrics, annotations = compute_metrics(transcription, str(audio_path))

    # Retake linking: inherit the parent's target so attempts are comparable.
    parent = db.get_session(parent_id) if parent_id else None
    if parent is not None and not coaching_target:
        coaching_target = parent.coaching_target or ""

    target_bands = profiles.target_bands(coaching_target)
    scores = compute_scores(metrics, transcription.duration_sec, target_bands)

    topic = Topic(category=topic_category, prompt=topic_prompt)
    # Coaching is opt-out via Settings; pass recent history + target/tone/depth.
    feedback = (
        coaching.generate_feedback(
            topic, transcription.text, metrics, scores, db.list_sessions(),
            target=coaching_target, tone=coaching_tone, depth=coaching_depth,
            annotations=annotations,
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
        coaching_target=coaching_target or None,
        parent_id=parent.id if parent else None,
        attempt=(parent.attempt + 1) if parent else 1,
    )
    db.save_session(session)
    return session


@app.get("/profiles", response_model=list[TargetInfo])
def get_profiles() -> list[TargetInfo]:
    return profiles.list_targets()


@app.post("/sessions/{session_id}/coach", response_model=Session)
def recoach(session_id: str, target: str = "", tone: str = "", depth: str = "") -> Session:
    """Re-score and re-coach an existing session against a (new) target.

    Pure function of the stored metrics + target bands (no audio needed), so the
    user can experiment with targets/tone/depth without re-recording.
    """
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session.scores = compute_scores(
        session.metrics, session.duration_sec, profiles.target_bands(target)
    )
    feedback = coaching.generate_feedback(
        session.topic, session.transcript, session.metrics, session.scores,
        db.list_sessions(), target=target, tone=tone, depth=depth,
        annotations=session.annotations,
    )
    if feedback is not None:
        session.feedback = feedback
    session.coaching_target = target or None
    db.save_session(session)
    return session


def _delete_recording_files() -> int:
    """Remove session + ideal audio files (top level of RECORDINGS_DIR).
    Leaves the voice/ enrollment subdirectory intact."""
    removed = 0
    for f in RECORDINGS_DIR.glob("*"):
        if f.is_file():
            f.unlink(missing_ok=True)
            removed += 1
    return removed


@app.delete("/recordings")
def delete_recordings() -> dict:
    """Delete stored audio only; keep sessions, stats, transcripts, scores."""
    files = _delete_recording_files()
    cleared = db.clear_media_paths()
    return {"deleted_files": files, "sessions_kept": cleared}


@app.delete("/sessions")
def delete_sessions() -> dict:
    """Delete ALL data: every session plus stored recordings (privacy)."""
    deleted = db.delete_all_sessions()
    _delete_recording_files()
    return {"deleted": deleted}


@app.put("/sessions/{session_id}/transcript", response_model=Session)
def edit_transcript(session_id: str, body: TranscriptUpdate) -> Session:
    """Replace a session's transcript (user correction before ideal delivery).

    Scores/acoustic metrics are not recomputed — this updates the text used for
    the ideal-delivery synthesis and what's displayed.
    """
    session = db.update_transcript(session_id, body.transcript.strip())
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


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
            to_wav_file(str(src), tmp, CLONE_SR)
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
        to_wav_file(str(tmp), str(ENROLLMENT_PATH), CLONE_SR)
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
def generate_ideal(
    session_id: str,
    provider: str | None = None,
    model: str | None = None,
    voice: str | None = None,
) -> Session:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.transcript.strip():
        raise HTTPException(status_code=400, detail="No transcript to synthesize")

    prov = tts.get_provider(provider)
    if prov is None:
        if provider:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown TTS provider '{provider}'. Options: {', '.join(tts.PROVIDERS)}.",
            )
        raise HTTPException(status_code=503, detail="No TTS provider configured (set TTS_PROVIDER).")
    if not prov.available():
        detail = f"TTS provider '{prov.name}' is unavailable — check its API key / install (requirements-tts.txt for local)."
        reason = getattr(prov, "reason", None)
        if reason:
            detail += f" ({reason})"
        raise HTTPException(status_code=503, detail=detail)

    # Cloning providers need a reference clip; preset-voice providers (OpenAI) don't.
    ref_path, is_temp = (None, False)
    if getattr(prov, "needs_voice_ref", True):
        ref_path, is_temp = _resolve_voice_ref(session)
        if ref_path is None:
            raise HTTPException(
                status_code=400,
                detail="No voice reference: enroll a voice sample in Settings, or enable 'keep recordings'.",
            )

    try:
        style_text, style_usage = coaching.generate_delivery_style(
            session.transcript, session.metrics, session.scores, session.coaching_target
        )
        pace = SCORING_CONFIG["pace"]
        target_wpm = (pace["ideal_min"] + pace["ideal_max"]) / 2
        user_wpm = session.metrics.wpm or target_wpm
        speed = max(0.7, min(1.3, target_wpm / user_wpm)) if user_wpm > 0 else 1.0
        style = {"instruction": style_text, "target_wpm": target_wpm, "speed": round(speed, 3)}
        if model:
            style["model"] = model
        if voice:
            style["voice"] = voice
        wav = prov.synthesize(session.transcript, ref_path, style)
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

    # Cost/usage accounting. Decode the result for a robust duration (OpenAI's
    # WAV header reports a bogus length).
    try:
        samples, sr = load_waveform(str(ideal_path))
        audio_seconds = len(samples) / sr if sr else 0.0
    except Exception:
        audio_seconds = 0.0
    eff_model = model or (
        os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts") if prov.name == "openai" else None
    )

    session.ideal_audio_path = str(ideal_path)
    session.delivery_style = style_text
    session.generation_usage = usage.build(
        prov.name, eff_model, session.transcript, style_usage, audio_seconds
    )
    try:
        usage_log.log(session_id, session.generation_usage)
    except Exception:
        pass  # never let logging break generation
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
