import { useCallback, useEffect, useState } from "react";
import Recorder from "./components/Recorder.jsx";
import TopicCard from "./components/TopicCard.jsx";
import Results from "./components/Results.jsx";
import Trends from "./components/Trends.jsx";
import { analyze, fetchTopic } from "./api.js";

export default function App() {
  const [view, setView] = useState("practice"); // practice | trends
  const [topic, setTopic] = useState(null);
  const [topicLoading, setTopicLoading] = useState(false);
  const [session, setSession] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | analyzing | error
  const [error, setError] = useState(null);

  const loadTopic = useCallback(async (tailored = false) => {
    setTopicLoading(true);
    setError(null);
    try {
      setTopic(await fetchTopic(tailored));
    } catch (err) {
      setError(err.message);
    } finally {
      setTopicLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTopic();
  }, [loadTopic]);

  async function handleRecorded(blob) {
    setStatus("analyzing");
    setError(null);
    setSession(null);
    try {
      const result = await analyze(blob, topic);
      setSession(result);
      setStatus("idle");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  // Clear the last result and pull a fresh topic for another attempt.
  function newTest() {
    setSession(null);
    setError(null);
    setStatus("idle");
    loadTopic();
  }

  const busy = status === "analyzing";

  return (
    <div className="app">
      <header>
        <h1>Speech Analyzer</h1>
        <p className="subtitle">Record 30–60s, then see how you sound.</p>
        <nav className="tabs">
          <button
            className={view === "practice" ? "tab active" : "tab"}
            onClick={() => setView("practice")}
          >
            Practice
          </button>
          <button
            className={view === "trends" ? "tab active" : "tab"}
            onClick={() => setView("trends")}
          >
            Trends
          </button>
        </nav>
      </header>

      {view === "trends" ? (
        <Trends />
      ) : (
        <>
          <TopicCard
            topic={topic}
            onShuffle={() => loadTopic(false)}
            onTailor={() => loadTopic(true)}
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
