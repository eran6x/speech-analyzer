# Speech Analyzer

A personal web application for analyzing and improving spoken delivery. Built for daily practice by a sales engineer who delivers frequent presentations, product demos, and customer/partner conversations.

> **This file is the project brief for Claude Code.** Read it fully before generating code. Build in the phases described in [Roadmap](#roadmap), starting from [Start Here](#start-here-first-task). Confirm the plan with the user before scaffolding if anything is ambiguous.

---

## Goal

A browser tool that:

1. Suggests a practice **topic** (small talk, presentation, job interview, promotion pitch, or custom).
2. Prompts the user to record a **30–60 second** audio clip.
3. Analyzes **how they sound** (acoustic — primary focus) and **what they said** (transcript — secondary).
4. Grades **1–100** across pace, pauses, confidence, and fluency, with strengths, weaknesses, and recommendations.
5. **Tracks every session** so progress is visible over time.

**Priority order:** acoustic delivery first (pitch, volume, pace, pauses, voice stability), transcript content second (fillers, hedging, structure).

---

## Tech Stack (decided — do not substitute without asking)

| Layer | Choice |
|---|---|
| Frontend | **React** (Vite), Recharts for trend charts |
| Audio capture | MediaRecorder + Web Audio API |
| Backend | **Python + FastAPI** |
| Speech-to-text | **faster-whisper** (word-level timestamps required) |
| Acoustic analysis | **parselmouth** (Praat) — covers pitch/intensity/pauses/jitter/shimmer/HNR through Phase 3; **librosa** not yet needed (audio decoding is handled by **av**) |
| Coaching layer | Anthropic Messages API (current Claude model) |
| Storage | **SQLite** (single file; migrate to Postgres only if ever needed) |

The user is comfortable running Python and code locally. The backend runs locally; no public hosting is required.

---

## Repository Structure (target)

```
speech-analyzer/
  CLAUDE.md                  # this file
  README.md
  backend/
    app/
      main.py                # FastAPI app + routes
      transcription.py       # faster-whisper wrapper (word timestamps)
      acoustic.py            # parselmouth + librosa feature extraction
      scoring.py             # raw metrics -> 1-100 scores
      coaching.py            # Anthropic API call for qualitative feedback
      db.py                  # SQLite access layer
      models.py              # pydantic schemas
      topics.py              # topic library + suggestion logic
    requirements.txt
    .env.example             # ANTHROPIC_API_KEY=...
  frontend/
    src/
      App.jsx
      components/
        Recorder.jsx         # record 30-60s, send to backend
        TopicCard.jsx        # shows suggested topic + prompt
        Results.jsx          # scores, metrics, coaching text
        Trends.jsx           # charts across sessions
      api.js                 # backend calls
    package.json
    vite.config.js
```

---

## API Contract (backend)

- `GET /topic` → `{ category, prompt }` — returns a suggested topic and a one-line speaking prompt.
- `POST /analyze` (multipart: audio file + `topic`) → full **Session** object (see schema).
- `GET /sessions` → list of past sessions (for trends).
- `GET /sessions/{id}` → single session detail.

---

## Data Model

A **Session** record (one per recording):

```
Session:
  id            : str (uuid)
  timestamp     : iso datetime
  topic         : { category, prompt }
  duration_sec  : float
  transcript    : str
  metrics:
    wpm                  : float   # words per minute (incl. pauses)
    articulation_rate    : float   # words per minute excluding pauses
    mean_pitch_hz        : float
    pitch_variability    : float   # std dev or coefficient of variation of F0
    mean_intensity_db    : float
    volume_stability     : float   # lower variability = steadier
    pause_count          : int
    mean_pause_sec       : float
    filler_count         : int
    filler_density       : float   # fillers per 100 words
    upspeak_count        : int     # rising F0 on declarative endings
    hedge_count          : int     # "sort of", "I think", "just", etc.
    jitter               : float   # phase 2
    shimmer              : float   # phase 2
  scores:
    pace        : int (1-100)
    pauses      : int (1-100)
    confidence  : int (1-100)
    fluency     : int (1-100)
    overall     : int (1-100)
  feedback      : str   # LLM coaching text
  audio_path    : str | null
```

---

## Metric Definitions

### Acoustic (primary)
- **Pitch (F0):** mean, range, variability. Monotone (low variability) = disengaging; healthy variation = expressive. Use parselmouth `to_pitch()`.
- **Upspeak:** rising F0 over the final segment of a declarative sentence. Flag occurrences — makes statements sound like questions and undermines authority.
- **Intensity/volume:** mean, range, stability via parselmouth `to_intensity()`. Trailing off at sentence ends signals low confidence.
- **Pace:** `wpm` from word count / duration. `articulation_rate` excludes pauses. Use whisper word timestamps.
- **Pauses:** detect silent gaps (intensity below threshold for > ~250ms). Count, mean length, placement.
- **Voice stability (phase 2):** jitter, shimmer, HNR via parselmouth.

### Transcript (secondary)
- **Filler density:** "um", "uh", "er" per 100 words.
- **Hedging:** "sort of", "kind of", "maybe", "I think", "just", "I guess" — track count.
- **False starts / repetitions:** repeated or abandoned phrases.

---

## Scoring Model (1–100, tunable)

Keep weights/ranges in a single config block so they're easy to adjust.

- **Pace** — peaks inside ~130–160 wpm; penalize too-fast (>180) and too-slow (<110); reward consistency.
- **Pauses** — reward deliberate silent pauses at sentence boundaries; penalize filled pauses and excessive hesitation gaps.
- **Confidence** — composite: healthy pitch variation + volume projection/stability + absence of upspeak + low hedging.
- **Fluency** — filler density + false-start/repetition rate + articulation smoothness.
- **Overall** — weighted blend (start equal-weighted; expose weights in config).

The numbers say **what**; the coaching layer says **why and how to fix it**.

---

## Coaching Layer

After metrics are computed, send transcript + metrics + topic + recent history to the Anthropic Messages API. Ask for:
- What went well (specific).
- What to fix (specific, tied to the metrics).
- One concrete recommendation for next time.
- One targeted drill for the lowest-scoring dimension.

Keep the API key in `.env` (`ANTHROPIC_API_KEY`); never hardcode it. For the current model name and request format, see the API docs linked below — do not guess the model string.

---

## Roadmap

### Phase 1 — MVP
- React recorder (30–60s) + topic card.
- `POST /analyze`: faster-whisper transcription with word timestamps.
- Core acoustic features: pitch, intensity, pauses, wpm.
- Rule-based scoring (pace, pauses, confidence, fluency, overall).
- Results view: scores + key metrics + basic coaching text.
- Persist each session to SQLite.
- Topic suggestion from a static list, random pick.

### Phase 2 — Depth & trends
- Trends view with charts across sessions.
- Add upspeak, hedging, and voice-quality (jitter/shimmer/HNR) metrics.
- LLM-generated topics tailored to weak areas.
- Targeted drills for the lowest-scoring dimension.

### Phase 3 — Polish & motivation
- Side-by-side compare of two sessions.
- Daily streaks and goal setting.
- Annotated waveform playback (mark where fillers/upspeak occurred).
- Exportable progress report.

---

## Start Here (First Task)

Build the **thinnest end-to-end slice** before anything else:

1. Scaffold `backend/` (FastAPI) and `frontend/` (Vite + React).
2. Frontend: a single page that records 30–60s and POSTs the audio to `/analyze`.
3. Backend `/analyze`: transcribe with faster-whisper, compute **wpm** and **pause count**, return a single **pace score** plus the transcript.
4. Frontend: display the score, wpm, pause count, and transcript.
5. Save the session to SQLite.

Once audio flows through the full loop, every other metric is an addition rather than a rebuild. Get this working and runnable (`README.md` with run steps) before expanding to the full metric set.

---

## Conventions / Guardrails

- Keep the scoring config (ideal ranges, weights) in one place.
- Type everything with pydantic on the backend.
- Don't add a database server, auth, or cloud hosting in Phase 1 — local SQLite only.
- Don't hardcode secrets; use `.env`.
- Prefer small, readable functions over cleverness — this is a tool the owner will keep extending.
- Provide `requirements.txt` and `package.json` with pinned versions, and a `README.md` with exact run commands.

---

## Reference Docs (verify current details here — don't rely on memory)

- Claude API overview: https://docs.claude.com/en/api/overview
- Claude API docs map: https://docs.claude.com/en/docs_site_map.md
- Claude Code overview: https://docs.claude.com/en/docs/claude-code/overview
- faster-whisper, parselmouth (Praat), librosa: see each library's own docs for current APIs.
