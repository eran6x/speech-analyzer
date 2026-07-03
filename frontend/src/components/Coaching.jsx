import { DIMENSION_COLORS } from "../colors.js";

// Renders coaching feedback as styled HTML sections (no markdown/asterisks),
// with pace/pauses/confidence/fluency words colored to match the scores.

const SECTIONS = ["What landed", "Sharpen the delivery", "Next time", "Drill"];

const DIM_WORD = {
  pace: "pace",
  pauses: "pauses",
  pause: "pauses",
  confidence: "confidence",
  fluency: "fluency",
};

function clean(text) {
  return (text || "")
    .replace(/\*\*(.*?)\*\*/g, "$1") // strip **bold**
    .replace(/[*#`_]/g, "") // strip stray markdown chars
    .replace(/^\s*[-•]\s+/gm, "") // strip bullet markers
    .trim();
}

function parseSections(text) {
  const heading = (line) => {
    const t = line.trim().replace(/:$/, "");
    return SECTIONS.find((s) => s.toLowerCase() === t.toLowerCase()) || null;
  };
  const sections = [];
  let cur = null;
  for (const line of text.split(/\r?\n/)) {
    const h = heading(line);
    if (h) {
      cur = { title: h, body: [] };
      sections.push(cur);
    } else if (cur && line.trim()) {
      cur.body.push(line.trim());
    }
  }
  return sections;
}

function colorize(text) {
  const parts = text.split(/(\bpace\b|\bpauses\b|\bpause\b|\bconfidence\b|\bfluency\b)/gi);
  return parts.map((p, i) => {
    const dim = DIM_WORD[p?.toLowerCase()];
    return dim ? (
      <strong key={i} style={{ color: DIMENSION_COLORS[dim] }}>{p}</strong>
    ) : (
      <span key={i}>{p}</span>
    );
  });
}

export default function Coaching({ text }) {
  const cleaned = clean(text);
  if (!cleaned) return <p className="settings-hint">No coaching.</p>;

  const sections = parseSections(cleaned);
  if (sections.length === 0) {
    // Legacy / unstructured feedback — render as spaced paragraphs.
    return (
      <div className="coach">
        {cleaned.split(/\n{2,}/).map((para, i) => (
          <p className="coach-body" key={i}>{colorize(para)}</p>
        ))}
      </div>
    );
  }

  return (
    <div className="coach">
      {sections.map((s, i) => (
        <div className="coach-section" key={i}>
          <h4 className="coach-title">{s.title}</h4>
          <p className="coach-body">{colorize(s.body.join(" "))}</p>
        </div>
      ))}
    </div>
  );
}
