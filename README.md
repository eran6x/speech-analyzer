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

**App shell:** five tabs — **Home** (greeting + streak/goals + progress chart),
**Practice** (scenario buttons + recording, collapsible playback/stats/
transcript), **Trends**, **Help** (what every score/metric means), and
**Settings** (account/privacy/security/general — stored locally, future-proofed).

**Phase 3 (this round):**
- **Daily streaks & goals** on Home — current/longest streak, sessions this
  week, and editable targets (avg overall score, sessions/week) with progress
  bars (`GET /stats`).
- **Annotated waveform playback** — play your recording back with colored
  markers for pauses, fillers, hedges, and upspeak; click a marker to jump
  there (WaveSurfer.js + `GET /sessions/{id}/audio`). Statistics colors match
  the trend-line colors for pace/pauses/confidence/fluency.

Settings wiring (delete-all, keep-recordings, coaching toggle) is now live.
Remaining: session compare + exportable report → [Phase5_plan.md](Phase5_plan.md).
Licensing (AGPLv3 + commercial use) → [Phase4_plan.md](Phase4_plan.md).
Phase 3 designs → [Phase3_plan.md](Phase3_plan.md).

**Phase 6 (voice-cloned "ideal delivery") — core landed:** after a session,
"✨ Hear ideal delivery" generates the same transcript spoken back in a clone of
your voice with optimal delivery, shown as an A/B player against your recording.
Pluggable TTS (`TTS_PROVIDER`, default local Coqui XTTS-v2; ElevenLabs stubbed
for the hosted roadmap), Claude-authored delivery style, voice enrollment in
Settings with per-session fallback. The local engine needs
[backend/requirements-tts.txt](backend/requirements-tts.txt) + a GPU. Design +
cloud roadmap → [Phase6_plan.md](Phase6_plan.md).

**Phase 7 (core landed):** delivery-craft coaching (emphasis, vocal variety,
pacing-for-effect, structure) — steerable via **target style/goal, tone &
depth**, and able to target curated **famous-speaker profiles** (Jobs, Obama,
Brené Brown, Churchill, Oprah) with **target-relative scoring** and a
you-vs-them comparison. Re-coach any session against a different target without
re-recording. Design → [Phase7_plan.md](Phase7_plan.md).

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

All Python dependencies are pinned in [backend/requirements.txt](backend/requirements.txt)
(FastAPI/uvicorn, pydantic, faster-whisper, av, numpy, praat-parselmouth,
anthropic, requests). Note: `librosa` from the original tech stack isn't
required — parselmouth covers the acoustic analysis through Phase 3.

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
