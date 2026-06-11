import { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import RegionsPlugin from "wavesurfer.js/dist/plugins/regions.esm.js";
import { audioUrl } from "../api.js";

// Marker colors per annotation kind (translucent so the waveform shows through).
const KIND_COLORS = {
  pause: "rgba(154, 160, 173, 0.35)",
  filler: "rgba(255, 135, 135, 0.35)",
  hedge: "rgba(218, 119, 242, 0.35)",
  upspeak: "rgba(255, 212, 59, 0.35)",
};

export default function WaveformPlayer({ session }) {
  const containerRef = useRef(null);
  const wsRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;
    const regions = RegionsPlugin.create();
    const ws = WaveSurfer.create({
      container: containerRef.current,
      url: audioUrl(session.id),
      height: 88,
      waveColor: "#3a3f4b",
      progressColor: "#6ea8fe",
      cursorColor: "#e7e9ee",
      barWidth: 2,
      barGap: 1,
      plugins: [regions],
    });
    wsRef.current = ws;

    ws.on("decode", () => {
      for (const a of session.annotations || []) {
        regions.addRegion({
          start: a.start,
          end: Math.max(a.end, a.start + 0.04),
          content: a.label,
          color: KIND_COLORS[a.kind] || "rgba(110,168,254,0.3)",
          drag: false,
          resize: false,
        });
      }
    });
    ws.on("play", () => setPlaying(true));
    ws.on("pause", () => setPlaying(false));
    ws.on("finish", () => setPlaying(false));
    ws.on("error", () => setError(true));
    // Click a marker to jump there.
    regions.on("region-clicked", (region, e) => {
      e.stopPropagation();
      ws.setTime(region.start);
      ws.play();
    });

    return () => ws.destroy();
  }, [session.id]);

  if (error) {
    return <p className="status">Could not load audio for playback.</p>;
  }

  return (
    <div className="waveform">
      <div ref={containerRef} className="waveform-canvas" />
      <div className="waveform-controls">
        <button
          className="primary-btn"
          onClick={() => wsRef.current?.playPause()}
        >
          {playing ? "❚❚ Pause" : "▶ Play"}
        </button>
        <div className="waveform-legend">
          {Object.entries(KIND_COLORS).map(([kind, color]) => (
            <span key={kind} className="dim-legend-item">
              <span className="dim-swatch" style={{ background: color }} />
              {kind}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
