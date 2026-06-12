import { useState } from "react";
import { DIMENSION_COLORS, METRIC_DIMENSION } from "../colors.js";
import { audioUrl, generateIdeal, idealAudioUrl } from "../api.js";
import WaveformPlayer from "./WaveformPlayer.jsx";

export default function Results({ session }) {
  const [ideal, setIdeal] = useState(null); // session updated with ideal audio
  const [genStatus, setGenStatus] = useState("idle"); // idle | loading | error
  const [genError, setGenError] = useState(null);

  if (!session) return null;
  const { scores, metrics, transcript, duration_sec, feedback } = session;

  async function makeIdeal() {
    setGenStatus("loading");
    setGenError(null);
    try {
      setIdeal(await generateIdeal(session.id));
      setGenStatus("idle");
    } catch (e) {
      setGenError(e.message);
      setGenStatus("error");
    }
  }

  return (
    <div className="card results">
      <div className="score-hero">
        <div className="score-circle">{scores.overall ?? scores.pace}</div>
        <div className="score-label">Overall</div>
      </div>

      <div className="subscore-row">
        <Subscore label="Pace" value={scores.pace} dim="pace" />
        <Subscore label="Pauses" value={scores.pauses} dim="pauses" />
        <Subscore label="Confidence" value={scores.confidence} dim="confidence" />
        <Subscore label="Fluency" value={scores.fluency} dim="fluency" />
      </div>

      {feedback && (
        <div className="feedback">
          <h3>Coaching</h3>
          <p className="feedback-text">{feedback}</p>
        </div>
      )}

      {session.id && (session.audio_path || ideal) && (
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

          {ideal?.ideal_audio_path ? (
            <div className="ideal-block">
              <p className="playback-label">Ideal delivery (your voice)</p>
              {ideal.delivery_style && (
                <p className="ideal-style">🎯 {ideal.delivery_style}</p>
              )}
              <WaveformPlayer url={idealAudioUrl(session.id)} />
            </div>
          ) : (
            <div className="ideal-cta">
              <button
                className="primary-btn"
                onClick={makeIdeal}
                disabled={genStatus === "loading"}
              >
                {genStatus === "loading"
                  ? "Generating…"
                  : "✨ Hear ideal delivery"}
              </button>
              {genError && <p className="error">{genError}</p>}
            </div>
          )}
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
        <p className="transcript">{transcript || "(no speech detected)"}</p>
      </details>
    </div>
  );
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
