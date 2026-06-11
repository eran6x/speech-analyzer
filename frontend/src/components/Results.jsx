export default function Results({ session }) {
  if (!session) return null;
  const { scores, metrics, transcript, duration_sec, feedback } = session;

  return (
    <div className="card results">
      <div className="score-hero">
        <div className="score-circle">{scores.overall ?? scores.pace}</div>
        <div className="score-label">Overall</div>
      </div>

      <div className="subscore-row">
        <Subscore label="Pace" value={scores.pace} />
        <Subscore label="Pauses" value={scores.pauses} />
        <Subscore label="Confidence" value={scores.confidence} />
        <Subscore label="Fluency" value={scores.fluency} />
      </div>

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

      {feedback && (
        <div className="feedback">
          <h3>Coaching</h3>
          <p className="feedback-text">{feedback}</p>
        </div>
      )}

      <h3>Transcript</h3>
      <p className="transcript">{transcript || "(no speech detected)"}</p>
    </div>
  );
}

const fmt = (v) => (v == null ? "—" : v);
const secs = (v) => (v == null ? "—" : `${v}s`);
const hz = (v) => (v == null ? "—" : `${Math.round(v)} Hz`);
const db = (v) => (v == null ? "—" : `${v.toFixed(1)} dB`);
const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

function Subscore({ label, value }) {
  return (
    <div className="subscore">
      <div className="subscore-value">{value ?? "—"}</div>
      <div className="subscore-label">{label}</div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}
