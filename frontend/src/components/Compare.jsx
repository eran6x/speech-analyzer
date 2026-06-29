import { useEffect, useState } from "react";
import { fetchSessions } from "../api.js";
import { DIMENSION_COLORS } from "../colors.js";

const SCORES = [
  ["overall", "Overall", DIMENSION_COLORS.overall],
  ["pace", "Pace", DIMENSION_COLORS.pace],
  ["pauses", "Pauses", DIMENSION_COLORS.pauses],
  ["confidence", "Confidence", DIMENSION_COLORS.confidence],
  ["fluency", "Fluency", DIMENSION_COLORS.fluency],
];

// [metric key, label, value formatter]
const METRICS = [
  ["wpm", "Words / min", (v) => fmtNum(v)],
  ["articulation_rate", "Articulation", (v) => fmtNum(v)],
  ["mean_pitch_hz", "Pitch", (v) => (v == null ? "—" : `${Math.round(v)} Hz`)],
  ["pitch_variability", "Pitch range", (v) => (v == null ? "—" : `${Math.round(v)} Hz`)],
  ["mean_intensity_db", "Volume", (v) => (v == null ? "—" : `${v.toFixed(1)} dB`)],
  ["pause_count", "Pauses", (v) => fmtNum(v)],
  ["mean_pause_sec", "Mean pause", (v) => (v == null ? "—" : `${v}s`)],
  ["filler_count", "Fillers", (v) => fmtNum(v)],
  ["hedge_count", "Hedges", (v) => fmtNum(v)],
  ["upspeak_count", "Upspeak", (v) => fmtNum(v)],
];

export default function Compare() {
  const [sessions, setSessions] = useState(null);
  const [error, setError] = useState(null);
  const [ai, setAi] = useState(0);
  const [bi, setBi] = useState(0);

  useEffect(() => {
    fetchSessions()
      .then((list) => {
        setSessions(list);
        if (list.length) {
          setBi(list.length - 1); // latest
          setAi(Math.max(0, list.length - 2)); // the one before
        }
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!sessions) return <p className="status">Loading…</p>;
  if (sessions.length < 2) {
    return (
      <div className="card">
        <p className="status">Record at least two sessions to compare.</p>
      </div>
    );
  }

  const A = sessions[ai];
  const B = sessions[bi];

  return (
    <div className="card">
      <div className="cmp-pickers">
        <SessionPicker sessions={sessions} value={ai} onChange={setAi} />
        <SessionPicker sessions={sessions} value={bi} onChange={setBi} />
      </div>

      <div className="cmp-head">
        <span />
        <span>A · {A.timestamp.slice(0, 10)}</span>
        <span>B · {B.timestamp.slice(0, 10)}</span>
        <span>Δ</span>
      </div>

      <h4 className="section-subtitle">Scores</h4>
      {SCORES.map(([key, label, color]) => (
        <Row
          key={key}
          label={label}
          color={color}
          a={A.scores?.[key]}
          b={B.scores?.[key]}
          fmt={(v) => (v == null ? "—" : v)}
          goodHigh
        />
      ))}

      <h4 className="section-subtitle">Metrics</h4>
      {METRICS.map(([key, label, fmt]) => (
        <Row
          key={key}
          label={label}
          a={A.metrics?.[key]}
          b={B.metrics?.[key]}
          fmt={fmt}
        />
      ))}

      <div className="cmp-cols">
        <TextCol title="A — transcript" body={A.transcript} />
        <TextCol title="B — transcript" body={B.transcript} />
      </div>
      <div className="cmp-cols">
        <TextCol title="A — coaching" body={A.feedback} />
        <TextCol title="B — coaching" body={B.feedback} />
      </div>
    </div>
  );
}

function SessionPicker({ sessions, value, onChange }) {
  return (
    <select value={value} onChange={(e) => onChange(Number(e.target.value))}>
      {sessions.map((s, i) => (
        <option key={s.id} value={i}>
          {s.timestamp.slice(0, 10)} · {s.topic.category} · {s.scores?.overall ?? "—"}
        </option>
      ))}
    </select>
  );
}

function Row({ label, color, a, b, fmt, goodHigh = false }) {
  const delta = typeof a === "number" && typeof b === "number" ? b - a : null;
  let cls = "neutral";
  let text = "";
  if (delta != null && delta !== 0) {
    const up = delta > 0;
    text = `${up ? "▲ +" : "▼ "}${fmtNum(delta)}`;
    cls = goodHigh ? (up ? "up" : "down") : "neutral";
  } else if (delta === 0) {
    text = "–";
  }
  return (
    <div className="cmp-row">
      <span className="cmp-dim" style={color ? { color } : undefined}>{label}</span>
      <span className="cmp-a">{fmt(a)}</span>
      <span className="cmp-b">{fmt(b)}</span>
      <span className={`cmp-delta ${cls}`}>{text}</span>
    </div>
  );
}

function TextCol({ title, body }) {
  return (
    <div className="cmp-col">
      <h4>{title}</h4>
      <p>{body || "—"}</p>
    </div>
  );
}

function fmtNum(v) {
  if (v == null) return "—";
  return Number.isInteger(v) ? `${v}` : `${Math.round(v * 10) / 10}`;
}
