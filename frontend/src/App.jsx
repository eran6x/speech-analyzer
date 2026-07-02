import { useCallback, useEffect, useState } from "react";
import Recorder from "./components/Recorder.jsx";
import TopicCard from "./components/TopicCard.jsx";
import ScenarioPicker from "./components/ScenarioPicker.jsx";
import Results from "./components/Results.jsx";
import Trends from "./components/Trends.jsx";
import Compare from "./components/Compare.jsx";
import AttemptDiff from "./components/AttemptDiff.jsx";
import ConversationRunner from "./components/ConversationRunner.jsx";
import Home from "./components/Home.jsx";
import Help from "./components/Help.jsx";
import Settings from "./components/Settings.jsx";
import { analyze, fetchCategories, fetchTopic } from "./api.js";
import { loadSettings } from "./settings.js";

const TABS = ["Home", "Practice", "Trends", "Compare", "Help", "Settings"];

export default function App() {
  const [view, setView] = useState("Home");
  const [practiceMode, setPracticeMode] = useState("single"); // single | conversation
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [topic, setTopic] = useState(null);
  const [topicLoading, setTopicLoading] = useState(false);
  const [session, setSession] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | analyzing | error
  const [error, setError] = useState(null);
  const [retakeOf, setRetakeOf] = useState(null); // armed retake's parent
  const [baseline, setBaseline] = useState(null); // prior attempt to diff against

  const loadTopic = useCallback(async ({ tailored = false, category = null } = {}) => {
    setTopicLoading(true);
    setError(null);
    try {
      setTopic(await fetchTopic({ tailored, category }));
    } catch (err) {
      setError(err.message);
    } finally {
      setTopicLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => {});
    loadTopic();
  }, [loadTopic]);

  function resetAttempts() {
    setSession(null);
    setRetakeOf(null);
    setBaseline(null);
  }

  function pickCategory(category) {
    setSelectedCategory(category);
    resetAttempts();
    loadTopic({ category });
  }

  function pickTailored() {
    setSelectedCategory(null);
    resetAttempts();
    loadTopic({ tailored: true });
  }

  async function handleRecorded(blob) {
    const parent = retakeOf; // capture: this recording is a retake of `parent`
    setStatus("analyzing");
    setError(null);
    setSession(null);
    try {
      const s = loadSettings();
      const result = await analyze(blob, topic, {
        coaching: s.coachingEnabled,
        keepRecording: s.keepRecordings,
        // A retake inherits the parent's target so the diff is comparable.
        coachingTarget: parent ? parent.coaching_target || "" : s.coachingTarget,
        coachingTone: s.coachingTone,
        coachingDepth: s.coachingDepth,
        parentId: parent ? parent.id : undefined,
      });
      setBaseline(parent || null);
      setRetakeOf(null);
      setSession(result);
      setStatus("idle");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  // Same topic + target, links to the current attempt → before/after diff.
  function startRetake() {
    setRetakeOf(session);
    setBaseline(null);
    setError(null);
  }

  function newTest() {
    setError(null);
    setStatus("idle");
    resetAttempts();
    loadTopic({ category: selectedCategory });
  }

  const busy = status === "analyzing";

  return (
    <div className="app">
      <header>
        <h1>Speech Analyzer</h1>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t}
              className={view === t ? "tab active" : "tab"}
              onClick={() => setView(t)}
            >
              {t}
            </button>
          ))}
        </nav>
      </header>

      {view === "Home" && <Home onStart={() => setView("Practice")} />}
      {view === "Trends" && <Trends />}
      {view === "Compare" && <Compare />}
      {view === "Help" && <Help />}
      {view === "Settings" && <Settings />}

      {view === "Practice" && (
        <>
          <div className="mode-toggle">
            <button
              className={practiceMode === "single" ? "tab active" : "tab"}
              onClick={() => setPracticeMode("single")}
            >
              Single prompt
            </button>
            <button
              className={practiceMode === "conversation" ? "tab active" : "tab"}
              onClick={() => setPracticeMode("conversation")}
            >
              Conversation
            </button>
          </div>

          {practiceMode === "conversation" && (
            <ConversationRunner categories={categories} />
          )}

          {practiceMode === "single" && (
          <>
          <ScenarioPicker
            categories={categories}
            selected={selectedCategory}
            onPick={pickCategory}
            onTailor={pickTailored}
            disabled={busy || topicLoading}
          />
          <TopicCard
            topic={topic}
            onShuffle={() => loadTopic({ category: selectedCategory })}
            disabled={busy || topicLoading}
          />
          <Recorder
            onRecorded={handleRecorded}
            disabled={busy || topicLoading || !topic}
          />

          {retakeOf && !busy && (
            <p className="status">
              🔁 Retake of attempt {retakeOf.attempt} — record again to compare.
            </p>
          )}
          {topicLoading && <p className="status">Finding a topic…</p>}
          {busy && <p className="status">Analyzing your recording…</p>}
          {error && <p className="error">{error}</p>}

          {session && (
            <>
              {baseline && session.parent_id && (
                <AttemptDiff base={baseline} retake={session} />
              )}
              <Results key={session.id} session={session} />
              <div className="practice-actions">
                <button className="ghost-btn" onClick={startRetake}>
                  🔁 Try again (same topic)
                </button>
                <button className="primary-btn" onClick={newTest}>
                  ↻ New test
                </button>
              </div>
            </>
          )}
          </>
          )}
        </>
      )}
    </div>
  );
}
