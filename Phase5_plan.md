# Speech Analyzer — Phase 5 Plan

Features deferred from Phase 3. Full designs (API shapes, data-model changes,
UI) are in [Phase3_plan.md](Phase3_plan.md) — this file is the backlog pointer.

## 1. Session compare (Phase 3 Feature 1)

Side-by-side diff of two past sessions: score/metric deltas (▲/▼), both
transcripts, both coaching notes. Frontend on existing `/sessions` data; optional
`GET /sessions/compare?a=&b=` for server-side deltas.

## 2. Exportable progress report (Phase 3 Feature 4)

`GET /report?from=&to=&format=md|json|pdf` — trend charts, best/worst, averages,
streak, and an optional LLM-written progress summary (reuse `coaching.py`).
Start with Markdown/JSON; add PDF if wanted.

## 3. Wire Settings into the pipeline (Phase 3 Feature 5)

Move settings from browser localStorage to a backend `app_settings` table
(`GET/PUT /settings`) and make the load-bearing ones real:

- **Privacy → keep recordings off:** delete the audio file after analysis.
- **Privacy → delete all sessions:** `DELETE /sessions` (+ wipe `recordings/`).
- **General → AI coaching toggle:** gate `coaching.generate_feedback`.
- **General → target pace:** feed Home goals / pace-score band.

Keep passcode/reminders as future placeholders.

---

See [Phase4_plan.md](Phase4_plan.md) for licensing/distribution (AGPLv3 +
commercial-use note), which is independent of these features.
