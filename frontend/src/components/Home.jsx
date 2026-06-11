import Trends from "./Trends.jsx";
import { loadSettings } from "../settings.js";

export default function Home({ onStart }) {
  const name = loadSettings().displayName?.trim();

  return (
    <>
      <div className="card home-hero">
        <h2>Welcome{name ? `, ${name}` : ""} 👋</h2>
        <p>
          Speech Analyzer helps you sharpen how you sound. Pick a scenario,
          record a 30–60 second clip, and get scored on <strong>pace</strong>,{" "}
          <strong>pauses</strong>, <strong>confidence</strong>, and{" "}
          <strong>fluency</strong> — plus specific coaching on what to fix next.
        </p>
        <p className="home-howto">
          The analysis listens to <em>how</em> you sound (pitch, volume,
          pauses, steadiness) first, and <em>what</em> you said (fillers,
          hedging) second. Every session is saved so you can watch your progress
          below.
        </p>
        <button className="primary-btn" onClick={onStart}>
          Start practicing →
        </button>
      </div>

      <h3 className="section-title">Your progress</h3>
      <Trends />
    </>
  );
}
