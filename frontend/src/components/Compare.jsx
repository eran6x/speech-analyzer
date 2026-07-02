import { useEffect, useState } from "react";
import { fetchSessions } from "../api.js";
import ScoreMetricDiff from "./ScoreMetricDiff.jsx";

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

      <ScoreMetricDiff
        a={A}
        b={B}
        labelA={`A · ${A.timestamp.slice(0, 10)}`}
        labelB={`B · ${B.timestamp.slice(0, 10)}`}
      />

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

function TextCol({ title, body }) {
  return (
    <div className="cmp-col">
      <h4>{title}</h4>
      <p>{body || "—"}</p>
    </div>
  );
}
