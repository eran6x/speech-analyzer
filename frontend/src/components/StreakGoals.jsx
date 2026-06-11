import { useEffect, useState } from "react";
import { fetchStats } from "../api.js";
import { loadSettings, saveSettings } from "../settings.js";

export default function StreakGoals() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [goals, setGoals] = useState(() => {
    const s = loadSettings();
    return { overall: s.goalOverall, weekly: s.goalWeekly };
  });

  useEffect(() => {
    fetchStats().then(setStats).catch((e) => setError(e.message));
  }, []);

  function setGoal(key, value) {
    const next = { ...goals, [key]: value };
    setGoals(next);
    saveSettings({ ...loadSettings(), goalOverall: next.overall, goalWeekly: next.weekly });
  }

  if (error) return <p className="error">{error}</p>;
  if (!stats) return <p className="status">Loading…</p>;

  return (
    <div className="card">
      <div className="streak-row">
        <Stat value={`🔥 ${stats.current_streak}`} label="day streak" big />
        <Stat value={stats.longest_streak} label="longest" />
        <Stat value={stats.sessions_this_week} label="this week" />
        <Stat value={stats.total_sessions} label="total" />
      </div>

      <h4 className="goals-title">Goals</h4>
      <Goal
        label="Average overall score"
        current={stats.averages.overall ?? 0}
        target={goals.overall}
        onTarget={(v) => setGoal("overall", v)}
        min={1}
        max={100}
      />
      <Goal
        label="Sessions this week"
        current={stats.sessions_this_week}
        target={goals.weekly}
        onTarget={(v) => setGoal("weekly", v)}
        min={1}
        max={21}
      />
    </div>
  );
}

function Stat({ value, label, big }) {
  return (
    <div className={big ? "streak-stat big" : "streak-stat"}>
      <div className="streak-value">{value}</div>
      <div className="streak-label">{label}</div>
    </div>
  );
}

function Goal({ label, current, target, onTarget, min, max }) {
  const pct = target > 0 ? Math.min((current / target) * 100, 100) : 0;
  const met = current >= target;
  return (
    <div className="goal">
      <div className="goal-header">
        <span>{label}</span>
        <span className="goal-target">
          {round(current)} /{" "}
          <input
            type="number"
            min={min}
            max={max}
            value={target}
            onChange={(e) => onTarget(Number(e.target.value))}
          />
          {met && " ✓"}
        </span>
      </div>
      <div className="goal-bar">
        <div
          className="goal-fill"
          style={{ width: `${pct}%`, background: met ? "#63e6be" : "#6ea8fe" }}
        />
      </div>
    </div>
  );
}

const round = (v) => (Number.isInteger(v) ? v : Math.round(v * 10) / 10);
