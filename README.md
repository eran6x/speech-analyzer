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

**Phase 2 (complete):**
- **Trends** tab — line charts of overall + per-dimension scores (Recharts).
- **Voice-quality metrics** — jitter, shimmer, HNR (parselmouth).
- **Upspeak** detection — rising F0 on declarative endings, feeds confidence.
- **Tailored topics** — "✨ tailor to weak areas" asks Claude for a topic
  targeting your weakest recent dimension; random fallback without a key.

**App shell (current):** five tabs — **Home** (greeting + progress chart),
**Practice** (scenario buttons + recording, collapsible stats/transcript),
**Trends**, **Help** (what every score/metric means), and **Settings**
(account/privacy/security/general — stored locally, future-proofed).

Phase 3 (compare sessions, streaks/goals, annotated waveform playback,
exportable report, and wiring Settings into the pipeline) is planned in
[Phase3_plan.md](Phase3_plan.md).

The scoring config (ideal ranges + weights) lives in one place:
[backend/app/scoring.py](backend/app/scoring.py) → `CONFIG`.

## Requirements

- **Python 3.11 or 3.12** for the backend. (3.13+ is not yet supported by
  faster-whisper's native dependency `ctranslate2` / `pydantic-core`.)
- **Node 18+** for the frontend.

## Quick start (both at once)

Once the venv exists and `npm install` has run (see below), start/stop both
servers together:

```bash
./dev.sh start     # backend :8000 + frontend :5173 (loads backend/.env)
./dev.sh status
./dev.sh logs      # tail both logs
./dev.sh stop
./dev.sh restart
```

Logs and PIDs live in `.dev/` (git-ignored). The sections below cover first-time
setup and running each server manually.

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
