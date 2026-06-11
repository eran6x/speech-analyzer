# Speech Analyzer

A personal web app for analyzing spoken delivery. See
[Speech_analyer_plan.md](Speech_analyer_plan.md) for the full project brief.

**Current status: Phase 1 (MVP) complete.** Record a 30–60s clip and get:

- **Scores (1–100):** pace, pauses, confidence, fluency, and an overall blend.
- **Acoustic metrics** (parselmouth): mean pitch + pitch range, mean volume +
  volume steadiness, intensity-based pause detection (count + mean length),
  words-per-minute and articulation rate.
- **Transcript metrics:** filler count/density, hedging, false starts.
- **Coaching text** from Claude (`claude-opus-4-8`) — what went well, what to
  fix, a next-time tip, and a targeted drill. Skipped automatically if no API
  key is set.

Every session is saved to SQLite.

**Phase 2 (in progress):**
- **Trends** tab — line charts of overall + per-dimension scores across all
  saved sessions (Recharts).
- **Voice-quality metrics** — jitter, shimmer, HNR (parselmouth).
- **Upspeak** detection — rising F0 on declarative sentence endings, which
  feeds into the confidence score.
- **New test** button to clear the result and pull a fresh topic.
- **Tailored topics** — the "✨ tailor to weak areas" button asks Claude for a
  practice topic targeting your weakest recent dimension (`GET /topic?tailored=true`);
  falls back to a random topic without an API key or scored history.

Phase 2 is complete. Phase 3 (compare sessions, streaks, annotated waveform,
exportable report) is the next milestone.

The scoring config (ideal ranges + weights) lives in one place:
[backend/app/scoring.py](backend/app/scoring.py) → `CONFIG`.

## Requirements

- **Python 3.11 or 3.12** for the backend. (3.13+ is not yet supported by
  faster-whisper's native dependency `ctranslate2` / `pydantic-core`.)
- **Node 18+** for the frontend.

## Backend

```bash
cd backend
python3.11 -m venv ../.venv          # use a 3.11/3.12 interpreter
../.venv/bin/pip install -r requirements.txt
../.venv/bin/uvicorn app.main:app --reload --port 8000
```

The first `/analyze` call downloads the whisper `base` model (~140 MB) once.

- API docs: http://localhost:8000/docs
- SQLite file `backend/speech_analyzer.db` and raw clips in
  `backend/recordings/` are created on first run (both git-ignored).

**Coaching (optional):** copy `backend/.env.example` to `backend/.env` and set
`ANTHROPIC_API_KEY=...` to enable Claude-generated coaching. Without it,
analysis still returns full metrics and scores — just no coaching text. Load the
env file when launching, e.g. `set -a; source .env; set +a` before `uvicorn`.

Optional config (env vars, all have defaults): `WHISPER_MODEL`,
`WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`, `SPEECH_DB_PATH`, `RECORDINGS_DIR`.

## Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

The dev server expects the backend at `http://localhost:8000` (override with
`VITE_API_BASE`). Open the page, allow microphone access, record 30–60s, and
the scores appear when analysis finishes.

## API

| Method | Path | Description |
|---|---|---|
| `GET`  | `/topic` | Suggested topic + speaking prompt |
| `POST` | `/analyze` | multipart `audio` + `topic_category` + `topic_prompt` → Session |
| `GET`  | `/sessions` | All saved sessions |
| `GET`  | `/sessions/{id}` | One session |

## Project layout

```
backend/app/   main.py · transcription.py · audio_io.py · acoustic.py ·
               text_metrics.py · scoring.py · coaching.py · db.py · models.py · topics.py
frontend/src/  App.jsx · api.js · components/{Recorder,TopicCard,Results,Trends}.jsx
```
