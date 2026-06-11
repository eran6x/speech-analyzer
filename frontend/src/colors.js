// One source of truth for the score-dimension colors, so the Trends chart lines
// and the Practice scores/statistics stay visually in sync.
export const DIMENSION_COLORS = {
  overall: "#6ea8fe",
  pace: "#63e6be",
  pauses: "#ffd43b",
  confidence: "#ff8787",
  fluency: "#da77f2",
};

// Which score dimension each Practice statistic feeds into (for color coding).
export const METRIC_DIMENSION = {
  "Words / min": "pace",
  Articulation: "pace",
  Pauses: "pauses",
  "Mean pause": "pauses",
  Pitch: "confidence",
  "Pitch range": "confidence",
  Volume: "confidence",
  Upspeak: "confidence",
  Jitter: "confidence",
  Shimmer: "confidence",
  HNR: "confidence",
  Fillers: "fluency",
  Hedges: "fluency",
  Duration: null, // neutral
};
