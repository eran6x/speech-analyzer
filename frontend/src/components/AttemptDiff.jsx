import ScoreMetricDiff, { SCORE_DIMS } from "./ScoreMetricDiff.jsx";

const LABELS = { pace: "Pace", pauses: "Pauses", confidence: "Confidence", fluency: "Fluency" };
const IMPROVE = 3; // min score delta to count as a real change

// The 1–2 lowest-scoring dimensions of the base attempt — what the coaching
// would have targeted ("what to fix").
function focusDims(scores) {
  return SCORE_DIMS.filter((d) => typeof scores?.[d] === "number")
    .sort((a, b) => scores[a] - scores[b])
    .slice(0, 2);
}

export default function AttemptDiff({ base, retake }) {
  const focus = focusDims(base.scores);

  const improved = SCORE_DIMS.filter(
    (d) =>
      typeof base.scores?.[d] === "number" &&
      typeof retake.scores?.[d] === "number" &&
      retake.scores[d] - base.scores[d] >= IMPROVE
  ).length;
  const scored = SCORE_DIMS.filter((d) => typeof base.scores?.[d] === "number").length;

  const overallDelta =
    typeof base.scores?.overall === "number" && typeof retake.scores?.overall === "number"
      ? retake.scores.overall - base.scores.overall
      : null;

  const focusBits = focus.map((d) => {
    const delta = (retake.scores?.[d] ?? 0) - (base.scores?.[d] ?? 0);
    const mark = delta >= IMPROVE ? "✓" : delta <= -IMPROVE ? "✗" : "≈";
    const sign = delta > 0 ? `+${delta}` : `${delta}`;
    return `${LABELS[d]} ${sign} ${mark}`;
  });

  return (
    <div className="card retake-diff">
      <h3>Before → After</h3>
      <p className="retake-verdict">
        {overallDelta != null && (
          <strong className={overallDelta >= 0 ? "up" : "down"}>
            Overall {overallDelta >= 0 ? `+${overallDelta}` : overallDelta}
          </strong>
        )}{" "}
        · improved on {improved} of {scored}
        {focusBits.length > 0 && <> · focus: {focusBits.join(", ")}</>}
      </p>
      <ScoreMetricDiff
        a={base}
        b={retake}
        labelA={`Attempt ${base.attempt}`}
        labelB={`Attempt ${retake.attempt}`}
        focusDims={focus}
      />
    </div>
  );
}
