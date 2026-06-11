# Speech Analyzer — Phase 3 Plan

**Polish & motivation.** Phases 1–2 deliver the full record → analyze → score →
coach loop, trends, voice-quality metrics, and tailored topics. Phase 3 turns a
working tool into one the owner returns to daily: comparison, streaks/goals,
annotated playback, and exportable reports. It also wires up the future-proofed
**Settings** tab so privacy/account preferences actually take effect.

> Read [Speech_analyer_plan.md](Speech_analyer_plan.md) for the original brief
> and tech stack (do not substitute without asking). This file scopes Phase 3
> only. Keep the scoring config in one place, type everything with pydantic,
> stay on local SQLite, and keep secrets in `.env`.

---

## Goals

1. **Compare** two sessions side by side to see what changed.
2. **Motivate** with daily streaks and user-set goals.
3. **Explain** with annotated waveform playback — see *where* fillers, pauses,
   and upspeak happened.
4. **Share** progress via an exportable report.
5. **Honor settings** — make the Settings tab's privacy/account options real.

---

## Feature 1 — Side-by-side session compare

Compare any two sessions (e.g. first vs. latest, or two attempts at the same
scenario).

- **UI:** a new **Compare** view (or a control inside Trends). Two session
  pickers (dropdowns of past sessions, labeled by date + category + overall).
  Render the two Sessions in parallel columns: scores diff (with ▲/▼ deltas and
  color), metric-by-metric deltas, both transcripts, both coaching notes.
- **Backend:** no new endpoint strictly required — the frontend already has
  `GET /sessions`. Optionally add `GET /sessions/compare?a={id}&b={id}` that
  returns both plus a computed `deltas` block to keep diff logic server-side and
  testable.
- **Data model:** none.
- **Nice-to-have:** "compare to my average" mode (diff against the mean of the
  last N sessions).

## Feature 2 — Streaks & goals

- **Streaks:** count consecutive days with ≥1 session (timezone-aware, from
  `timestamp`). Show current streak + longest streak on **Home**. A small
  calendar heatmap of practice days is a stretch goal.
- **Goals:** let the user set targets (e.g. "overall ≥ 80", "pace in 130–160",
  "3 sessions/week"). Show progress toward each goal on Home; celebrate when
  met.
- **Backend:**
  - Streaks can be computed client-side from `/sessions`, or add
    `GET /stats` returning `{current_streak, longest_streak, total_sessions,
    sessions_this_week, averages}` (cleaner, testable).
  - Goals are user config → persist in a new `settings`/`goals` table (or the
    existing local Settings store, promoted to the backend). Endpoints:
    `GET /goals`, `PUT /goals`.
- **Data model:** new `Goal` schema `{ id, kind, target, window }` and a
  `goals` table; or a single-row `app_settings` JSON blob.

## Feature 3 — Annotated waveform playback

Play the recording back with markers showing where issues occurred.

- **UI:** waveform with a playhead (e.g. WaveSurfer.js, or a Canvas drawn from
  decoded PCM). Overlay markers/regions for: silent pauses, detected fillers,
  hedges, and upspeak sentences. Clicking a marker seeks playback there.
- **Backend changes — timestamps are the work here:**
  - Serve the stored audio: `GET /sessions/{id}/audio` streaming
    `audio_path` (guard against path traversal; only serve files under
    `RECORDINGS_DIR`).
  - Extend metrics to capture **time spans**, not just counts:
    - pauses: list of `{start, end}` (already computed in `acoustic.py`
      `_detect_pauses` — return the spans, not only the count).
    - fillers/hedges: char/word offsets → map to word timestamps from whisper.
    - upspeak: the sentence span already computed in `_compute_upspeak`.
  - Add an `annotations` field to the Session: `{ pauses: [...], fillers: [...],
    hedges: [...], upspeak: [...] }`, each entry `{start, end, label}`.
- **Data model:** add `annotations` to `Session` (optional; back-compat with old
  rows that lack it).

## Feature 4 — Exportable progress report

- **UI:** an **Export** button (Home or Trends) → downloadable report covering a
  date range: trend charts, best/worst sessions, averages, streak, and a short
  LLM-written summary of progress and focus areas.
- **Backend:** `GET /report?from=&to=&format=md|pdf|json`.
  - Markdown/JSON: straightforward from `/sessions`.
  - PDF: render server-side (reportlab/weasyprint) or client-side
    (print-to-PDF). Start with Markdown/JSON; add PDF if wanted.
  - LLM summary: reuse `coaching.py` with a "summarize my progress over this
    period" prompt; skip gracefully without an API key.

## Feature 5 — Make Settings real

The Settings tab (Account / Privacy / Security / General) currently persists to
`localStorage` only. Phase 3 wires the load-bearing ones:

- **Privacy → "Keep recordings after analysis":** when off, delete the audio
  file after metrics are computed (don't persist `audio_path`). Requires the
  setting to reach the backend → move settings to a backend `app_settings` table
  (`GET/PUT /settings`) or pass per-request.
- **Privacy → "Delete all sessions":** `DELETE /sessions` (and wipe
  `recordings/`). Confirm in the UI first.
- **General → "AI coaching feedback" toggle:** gate `coaching.generate_feedback`
  on this flag.
- **General → "Target pace (wpm)":** feed into the Home goals display and
  optionally the pace-score ideal band.
- **Account:** display name already used by Home greeting. Email is informational
  until/unless multi-user is introduced (out of scope — stays local-only).
- **Security → passcode / reminders:** keep as future placeholders.

---

## Suggested order

1. **Annotated playback timestamps** (Feature 3 backend) — highest-value,
   touches `acoustic.py`/`text_metrics.py`; do the span work first since other
   things build on richer metrics.
2. **Audio serving endpoint + waveform UI** (Feature 3 frontend).
3. **Streaks & goals** (Feature 2) — quick win, big motivation payoff.
4. **Settings wiring** (Feature 5) — needs a small backend settings store; pairs
   naturally with goals.
5. **Compare view** (Feature 1).
6. **Exportable report** (Feature 4) — last, builds on everything above.

---

## API additions (summary)

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/sessions/{id}/audio` | Stream stored recording for playback |
| `GET`  | `/stats` | Streak, totals, averages |
| `GET`/`PUT` | `/goals` | Read/update user goals |
| `GET`/`PUT` | `/settings` | Backend-persisted settings (privacy, coaching toggle, target pace) |
| `DELETE` | `/sessions` | Delete all sessions + recordings (privacy) |
| `GET`  | `/sessions/compare?a=&b=` | Two sessions + computed deltas (optional) |
| `GET`  | `/report?from=&to=&format=` | Exportable progress report |

## Data-model additions

- `Session.annotations`: `{ pauses, fillers, hedges, upspeak: [{start, end, label}] }` (optional).
- `Goal`: `{ id, kind, target, window }` + a `goals`/`app_settings` table.

## Guardrails (unchanged from the brief)

- Local SQLite only; no auth/cloud in this phase.
- Keep scoring/goal thresholds in config.
- Don't hardcode secrets; coaching/report LLM calls degrade gracefully without a
  key.
- Guard the audio endpoint against path traversal (serve only from
  `RECORDINGS_DIR`).
- Keep `annotations` optional so existing saved sessions still load.
