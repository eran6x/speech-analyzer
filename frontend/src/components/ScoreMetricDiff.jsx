import { DIMENSION_COLORS } from "../colors.js";

// Shared A│B│Δ diff of two sessions' scores + key metrics. Used by the Compare
// tab and the Practice retake before/after panel.

export const SCORE_DIMS = ["pace", "pauses", "confidence", "fluency"];

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

export default function ScoreMetricDiff({ a, b, labelA = "A", labelB = "B", focusDims = [] }) {
  return (
    <>
      <div className="cmp-head">
        <span />
        <span>{labelA}</span>
        <span>{labelB}</span>
        <span>Δ</span>
      </div>

      <h4 className="section-subtitle">Scores</h4>
      {SCORES.map(([key, label, color]) => (
        <Row
          key={key}
          label={label}
          color={color}
          a={a.scores?.[key]}
          b={b.scores?.[key]}
          fmt={(v) => (v == null ? "—" : v)}
          goodHigh
          focus={focusDims.includes(key)}
        />
      ))}

      <h4 className="section-subtitle">Metrics</h4>
      {METRICS.map(([key, label, fmt]) => (
        <Row key={key} label={label} a={a.metrics?.[key]} b={b.metrics?.[key]} fmt={fmt} />
      ))}
    </>
  );
}

function Row({ label, color, a, b, fmt, goodHigh = false, focus = false }) {
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
      <span className="cmp-dim" style={color ? { color } : undefined}>
        {label}
        {focus && <span className="focus-badge">focus</span>}
      </span>
      <span className="cmp-a">{fmt(a)}</span>
      <span className="cmp-b">{fmt(b)}</span>
      <span className={`cmp-delta ${cls}`}>{text}</span>
    </div>
  );
}

export function fmtNum(v) {
  if (v == null) return "—";
  return Number.isInteger(v) ? `${v}` : `${Math.round(v * 10) / 10}`;
}
