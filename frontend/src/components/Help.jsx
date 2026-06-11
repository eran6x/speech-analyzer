const SCORES = [
  ["Overall", "Equal-weighted blend of the four scores below — your headline number."],
  ["Pace", "How fast you speak. Peaks around 130–160 wpm; too fast (>180) or too slow (<110) loses points."],
  ["Pauses", "Rewards deliberate silent pauses at natural breaks; penalizes too few (rushing), too many (choppy), and filled pauses."],
  ["Confidence", "Composite of healthy pitch variation, volume projection and steadiness, minus hedging and upspeak."],
  ["Fluency", "Penalizes fillers and false starts/repetitions off a clean baseline."],
];

const METRICS = [
  ["Words / min (wpm)", "Speaking rate including pauses. Conversational sweet spot is ~130–160."],
  ["Articulation", "Speaking rate excluding pauses — how fast you talk when you're actually talking."],
  ["Pitch", "Average fundamental frequency (F0) of your voice, in Hz."],
  ["Pitch range", "Variation in pitch (Hz). Low = monotone/disengaging; healthy variation = expressive."],
  ["Volume", "Mean loudness (dB). A relative figure — depends on mic gain, so read trends, not absolutes."],
  ["Pauses", "Number of silent stretches longer than ~0.25s, detected from the volume contour."],
  ["Mean pause", "Average length of those silent pauses, in seconds."],
  ["Fillers", '"um", "uh", "er"… counted from the transcript.'],
  ["Hedges", '"sort of", "I think", "just", "maybe"… softeners that weaken statements.'],
  ["Upspeak", "Statements that end on a rising pitch (like a question) — undermines authority."],
  ["Jitter", "Cycle-to-cycle pitch instability. Lower is steadier; very high can sound shaky."],
  ["Shimmer", "Cycle-to-cycle loudness instability. Lower is steadier."],
  ["HNR", "Harmonics-to-noise ratio (dB) — voice clarity vs. breathiness. Higher is clearer."],
];

export default function Help() {
  return (
    <div className="card help">
      <h2>What the numbers mean</h2>
      <p className="help-intro">
        Acoustic delivery (how you sound) is the priority; transcript content
        (what you said) is secondary. All scores are 1–100.
      </p>

      <h3>Scores</h3>
      <dl className="help-list">
        {SCORES.map(([term, def]) => (
          <div className="help-item" key={term}>
            <dt>{term}</dt>
            <dd>{def}</dd>
          </div>
        ))}
      </dl>

      <h3>Metrics</h3>
      <dl className="help-list">
        {METRICS.map(([term, def]) => (
          <div className="help-item" key={term}>
            <dt>{term}</dt>
            <dd>{def}</dd>
          </div>
        ))}
      </dl>

      <p className="help-note">
        Scoring thresholds live in one config block on the backend
        (<code>scoring.py → CONFIG</code>) and are easy to tune.
      </p>
    </div>
  );
}
