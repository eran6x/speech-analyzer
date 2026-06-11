import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchSessions } from "../api.js";

const SERIES = [
  { key: "overall", color: "#6ea8fe" },
  { key: "pace", color: "#63e6be" },
  { key: "pauses", color: "#ffd43b" },
  { key: "confidence", color: "#ff8787" },
  { key: "fluency", color: "#da77f2" },
];

export default function Trends() {
  const [sessions, setSessions] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSessions()
      .then(setSessions)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!sessions) return <p className="status">Loading…</p>;
  if (sessions.length === 0) {
    return (
      <div className="card">
        <p className="status">No sessions yet. Record one to start tracking progress.</p>
      </div>
    );
  }

  // Sessions arrive oldest-first; index them for a compact x-axis.
  const data = sessions.map((s, i) => ({
    n: i + 1,
    date: s.timestamp.slice(0, 10),
    overall: s.scores.overall,
    pace: s.scores.pace,
    pauses: s.scores.pauses,
    confidence: s.scores.confidence,
    fluency: s.scores.fluency,
  }));

  const latest = sessions[sessions.length - 1];

  return (
    <div className="card">
      <h3>Scores over time ({sessions.length} sessions)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: -16 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.08)" />
          <XAxis dataKey="n" stroke="#9aa0ad" tick={{ fontSize: 12 }} />
          <YAxis domain={[0, 100]} stroke="#9aa0ad" tick={{ fontSize: 12 }} />
          <Tooltip
            contentStyle={{ background: "#1a1d27", border: "none", borderRadius: 8 }}
            labelFormatter={(n) => `Session ${n} · ${data[n - 1]?.date ?? ""}`}
          />
          <Legend />
          {SERIES.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              stroke={s.color}
              strokeWidth={s.key === "overall" ? 3 : 1.5}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      <p className="trends-latest">
        Latest overall: <strong>{latest.scores.overall}</strong> ·{" "}
        {latest.topic.category} · {latest.timestamp.slice(0, 10)}
      </p>
    </div>
  );
}
