import { useCallback, useEffect, useState } from "react";
import Recorder from "./components/Recorder.jsx";
import TopicCard from "./components/TopicCard.jsx";
import ScenarioPicker from "./components/ScenarioPicker.jsx";
import Results from "./components/Results.jsx";
import Trends from "./components/Trends.jsx";
import Home from "./components/Home.jsx";
import Help from "./components/Help.jsx";
import Settings from "./components/Settings.jsx";
import { analyze, fetchCategories, fetchTopic } from "./api.js";

const TABS = ["Home", "Practice", "Trends", "Help", "Settings"];

export default function App() {
  const [view, setView] = useState("Home");
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [topic, setTopic] = useState(null);
  const [topicLoading, setTopicLoading] = useState(false);
  const [session, setSession] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | analyzing | error
  const [error, setError] = useState(null);

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

  function pickCategory(category) {
    setSelectedCategory(category);
    setSession(null);
    loadTopic({ category });
  }

  function pickTailored() {
    setSelectedCategory(null);
    setSession(null);
    loadTopic({ tailored: true });
  }

  async function handleRecorded(blob) {
    setStatus("analyzing");
    setError(null);
    setSession(null);
    try {
      setSession(await analyze(blob, topic));
      setStatus("idle");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  function newTest() {
    setSession(null);
    setError(null);
    setStatus("idle");
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
      {view === "Help" && <Help />}
      {view === "Settings" && <Settings />}

      {view === "Practice" && (
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

          {topicLoading && <p className="status">Finding a topic…</p>}
          {busy && <p className="status">Analyzing your recording…</p>}
          {error && <p className="error">{error}</p>}

          {session && (
            <>
              <Results session={session} />
              <button className="primary-btn newtest" onClick={newTest}>
                ↻ New test
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
}
