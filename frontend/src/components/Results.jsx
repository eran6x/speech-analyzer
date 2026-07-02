import { useEffect, useState } from "react";
import { DIMENSION_COLORS, METRIC_DIMENSION } from "../colors.js";
import {
  audioUrl,
  fetchProfiles,
  generateIdeal,
  idealAudioUrl,
  recoach,
  updateTranscript,
} from "../api.js";
import { loadSettings } from "../settings.js";
import WaveformPlayer from "./WaveformPlayer.jsx";

export default function Results({ session }) {
  const [ideal, setIdeal] = useState(null); // session updated with ideal audio
  const [genStatus, setGenStatus] = useState("idle"); // idle | loading | error
  const [genError, setGenError] = useState(null);
  const [genProvider, setGenProvider] = useState(loadSettings().ttsProvider || "");
  const [genCount, setGenCount] = useState(0); // cache-bust the ideal audio url
  const [transcriptText, setTranscriptText] = useState(session?.transcript || "");
  const [savedTranscript, setSavedTranscript] = useState(session?.transcript || "");
  const [tStatus, setTStatus] = useState("idle"); // idle | saving | error
  const [tMsg, setTMsg] = useState(null);
  const [coached, setCoached] = useState(null); // session after a re-coach
  const [coachTarget, setCoachTarget] = useState(
    session?.coaching_target || loadSettings().coachingTarget || ""
  );
  const [reStatus, setReStatus] = useState("idle");
  const [reError, setReError] = useState(null);
  const [profiles, setProfiles] = useState([]);

  useEffect(() => {
    fetchProfiles().then(setProfiles).catch(() => {});
  }, []);

  if (!session) return null;
  // `coached` (a re-coach result) supersedes the original for scores/feedback.
  const current = coached || session;
  const { scores, metrics, duration_sec, feedback } = current;
  const profile = profiles.find((p) => p.id === current.coaching_target);

  async function recoachNow() {
    setReStatus("loading");
    setReError(null);
    try {
      const s = loadSettings();
      const updated = await recoach(session.id, {
        target: coachTarget,
        tone: s.coachingTone,
        depth: s.coachingDepth,
      });
      setCoached(updated);
      setReStatus("idle");
    } catch (e) {
      setReError(e.message);
      setReStatus("error");
    }
  }

  async function makeIdeal() {
    setGenStatus("loading");
    setGenError(null);
    try {
      const s = loadSettings();
      const updated = await generateIdeal(session.id, {
        provider: genProvider, // quick-switch overrides the Settings default
        model: s.ttsModel,
        voice: s.ttsVoice,
      });
      setIdeal(updated);
      setGenCount((c) => c + 1);
      setGenStatus("idle");
    } catch (e) {
      setGenError(e.message);
      setGenStatus("error");
    }
  }

  async function saveTranscript() {
    setTStatus("saving");
    setTMsg(null);
    try {
      const updated = await updateTranscript(session.id, transcriptText);
      setSavedTranscript(updated.transcript);
      setTranscriptText(updated.transcript);
      setIdeal(null); // previous ideal is stale; let them regenerate
      setTStatus("idle");
      setTMsg("Saved ✓");
    } catch (e) {
      setTStatus("error");
      setTMsg(e.message);
    }
  }

  return (
    <div className="card results">
      <div className="score-hero">
        <div className="score-circle">{scores.overall ?? scores.pace}</div>
        <div className="score-label">Overall</div>
        {profile && profile.id !== "balanced" && (
          <div className="score-vs">scored vs {profile.name}</div>
        )}
      </div>

      <div className="subscore-row">
        <Subscore label="Pace" value={scores.pace} dim="pace" />
        <Subscore label="Pauses" value={scores.pauses} dim="pauses" />
        <Subscore label="Confidence" value={scores.confidence} dim="confidence" />
        <Subscore label="Fluency" value={scores.fluency} dim="fluency" />
      </div>

      {profile && profile.id !== "balanced" && (
        <ProfileComparison profile={profile} metrics={metrics} duration={duration_sec} />
      )}

      <div className="feedback">
        <h3>Coaching</h3>
        <div className="coach-controls">
          <select
            value={coachTarget}
            onChange={(e) => setCoachTarget(e.target.value)}
            disabled={reStatus === "loading"}
            title="Coaching target"
          >
            <option value="">Balanced</option>
            {profiles.filter((p) => p.kind === "style").length > 0 && (
              <optgroup label="Styles">
                {profiles
                  .filter((p) => p.kind === "style")
                  .map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
              </optgroup>
            )}
            {profiles.filter((p) => p.kind === "speaker").length > 0 && (
              <optgroup label="Speakers">
                {profiles
                  .filter((p) => p.kind === "speaker")
                  .map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
              </optgroup>
            )}
          </select>
          <button
            className="ghost-btn"
            onClick={recoachNow}
            disabled={reStatus === "loading"}
          >
            {reStatus === "loading" ? "Re-coaching…" : "↻ Re-coach"}
          </button>
        </div>
        {reError && <p className="error">{reError}</p>}
        {feedback ? (
          <p className="feedback-text">{feedback}</p>
        ) : (
          <p className="settings-hint">No coaching (set ANTHROPIC_API_KEY or enable it in Settings).</p>
        )}
      </div>

      {session.id && (
        <details className="collapsible" open>
          <summary>Playback</summary>

          {session.audio_path && (
            <>
              <p className="playback-label">Your recording</p>
              <WaveformPlayer
                url={audioUrl(session.id)}
                annotations={session.annotations || []}
              />
            </>
          )}

          <div className="ideal-controls">
            <select
              value={genProvider}
              onChange={(e) => setGenProvider(e.target.value)}
              disabled={genStatus === "loading"}
              title="Voice engine for this generation"
            >
              <option value="">Default</option>
              <option value="openai">OpenAI (preset voice)</option>
              <option value="local">Local (your voice)</option>
              <option value="elevenlabs">ElevenLabs</option>
            </select>
            <button
              className="primary-btn"
              onClick={makeIdeal}
              disabled={genStatus === "loading"}
            >
              {genStatus === "loading"
                ? "Generating…"
                : ideal
                  ? "↻ Regenerate"
                  : "✨ Hear ideal delivery"}
            </button>
          </div>
          {genError && <p className="error">{genError}</p>}

          {ideal?.ideal_audio_path && (
            <div className="ideal-block">
              <p className="playback-label">Ideal delivery</p>
              {ideal.delivery_style && (
                <p className="ideal-style">🎯 {ideal.delivery_style}</p>
              )}
              {ideal.generation_usage && (
                <p className="ideal-usage">{fmtUsage(ideal.generation_usage)}</p>
              )}
              <WaveformPlayer url={`${idealAudioUrl(session.id)}?n=${genCount}`} />
            </div>
          )}
        </details>
      )}

      {current.conversation?.length > 0 && (
        <details className="collapsible" open>
          <summary>Conversation ({current.conversation.length} questions)</summary>
          {current.conversation.map((t, i) => (
            <div className="convo-turn" key={i}>
              <p className="convo-turn-q">{i + 1}. {t.question}</p>
              <p className="convo-turn-a">{t.answer || "(no answer captured)"}</p>
            </div>
          ))}
        </details>
      )}

      <details className="collapsible" open>
        <summary>Statistics</summary>
        <div className="metric-grid">
          <Metric label="Words / min" value={metrics.wpm} />
          <Metric label="Articulation" value={fmt(metrics.articulation_rate)} />
          <Metric label="Pauses" value={metrics.pause_count} />
          <Metric label="Mean pause" value={secs(metrics.mean_pause_sec)} />
          <Metric label="Pitch" value={hz(metrics.mean_pitch_hz)} />
          <Metric label="Pitch range" value={hz(metrics.pitch_variability)} />
          <Metric label="Volume" value={db(metrics.mean_intensity_db)} />
          <Metric label="Fillers" value={metrics.filler_count} />
          <Metric label="Hedges" value={metrics.hedge_count} />
          <Metric label="Upspeak" value={fmt(metrics.upspeak_count)} />
          <Metric label="Jitter" value={pct(metrics.jitter)} />
          <Metric label="Shimmer" value={pct(metrics.shimmer)} />
          <Metric label="HNR" value={db(metrics.hnr)} />
          <Metric label="Duration" value={`${duration_sec}s`} />
        </div>
        <DimensionLegend />
      </details>

      <details className="collapsible">
        <summary>Transcript</summary>
        <textarea
          className="transcript-edit"
          value={transcriptText}
          onChange={(e) => setTranscriptText(e.target.value)}
          rows={4}
          placeholder="(no speech detected)"
        />
        <div className="transcript-actions">
          <button
            className="ghost-btn"
            onClick={saveTranscript}
            disabled={tStatus === "saving" || transcriptText === savedTranscript}
          >
            {tStatus === "saving" ? "Saving…" : "Save transcript"}
          </button>
          {tMsg && <span className="settings-hint">{tMsg}</span>}
        </div>
        <p className="settings-hint">
          Correct the transcript before generating ideal delivery. Scores aren't
          recomputed from edits.
        </p>
      </details>
    </div>
  );
}

function fmtUsage(u) {
  const tail = `${u.provider}${u.model ? `/${u.model}` : ""}`;
  const cost = u.total_cost_usd != null ? `~$${u.total_cost_usd.toFixed(4)}` : "plan-dependent";
  const bits = [];
  if (u.style_input_tokens != null)
    bits.push(`style ${u.style_input_tokens}→${u.style_output_tokens} tok`);
  if (u.tts_audio_seconds != null) bits.push(`${u.tts_audio_seconds}s audio`);
  else if (u.tts_characters != null) bits.push(`${u.tts_characters} chars`);
  return `Est. cost ${cost}${bits.length ? ` · ${bits.join(" · ")}` : ""} · ${tail}`;
}

const fmt = (v) => (v == null ? "—" : v);
const secs = (v) => (v == null ? "—" : `${v}s`);
const hz = (v) => (v == null ? "—" : `${Math.round(v)} Hz`);
const db = (v) => (v == null ? "—" : `${v.toFixed(1)} dB`);
const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

function Subscore({ label, value, dim }) {
  const color = DIMENSION_COLORS[dim];
  return (
    <div className="subscore" style={{ borderTop: `3px solid ${color}` }}>
      <div className="subscore-value" style={{ color }}>
        {value ?? "—"}
      </div>
      <div className="subscore-label">{label}</div>
    </div>
  );
}

function Metric({ label, value }) {
  const dim = METRIC_DIMENSION[label];
  const color = dim ? DIMENSION_COLORS[dim] : "rgba(255,255,255,0.15)";
  return (
    <div className="metric" style={{ borderLeft: `3px solid ${color}` }}>
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}

// "You vs {speaker}" — user metrics against the profile's target bands.
function ProfileComparison({ profile, metrics, duration }) {
  const b = profile.bands || {};
  const rows = [];
  const add = (label, value, band, unit) => {
    if (!band || value == null) return;
    const [lo, hi] = band;
    const mark = value < lo ? "▼" : value > hi ? "▲" : "✓";
    rows.push({
      label,
      value: `${Math.round(value)}${unit}`,
      band: `${Math.round(lo)}–${Math.round(hi)}${unit}`,
      mark,
    });
  };
  add("Pace", metrics.wpm, b.wpm, " wpm");
  add("Pitch range", metrics.pitch_variability, b.pitch_variability_hz, " Hz");
  const ppm = duration > 0 ? (metrics.pause_count / duration) * 60 : null;
  add("Pauses", ppm, b.pauses_per_min, "/min");
  if (rows.length === 0) return null;
  return (
    <div className="compare">
      <div className="compare-title">You vs {profile.name}</div>
      {rows.map((r) => (
        <div className="compare-row" key={r.label}>
          <span className="compare-label">{r.label}</span>
          <span className="compare-val">{r.value}</span>
          <span className={`compare-mark ${r.mark === "✓" ? "ok" : "off"}`}>{r.mark}</span>
          <span className="compare-band">target {r.band}</span>
        </div>
      ))}
    </div>
  );
}

// Tiny key tying the stat colors back to the four scored dimensions.
function DimensionLegend() {
  return (
    <div className="dim-legend">
      {["pace", "pauses", "confidence", "fluency"].map((d) => (
        <span key={d} className="dim-legend-item">
          <span
            className="dim-swatch"
            style={{ background: DIMENSION_COLORS[d] }}
          />
          {d}
        </span>
      ))}
    </div>
  );
}
