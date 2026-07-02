import { useState } from "react";
import Recorder from "./Recorder.jsx";
import Results from "./Results.jsx";
import { analyzeConversation, fetchConversationQuestions } from "../api.js";
import { loadSettings } from "../settings.js";

const STAGES = ["Icebreaker", "Follow-up", "Deepener"];

export default function ConversationRunner({ categories }) {
  const [phase, setPhase] = useState("setup"); // setup|loading|answering|finalizing|done|error
  const [category, setCategory] = useState(categories[0] || "small talk");
  const [questions, setQuestions] = useState([]);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [currentBlob, setCurrentBlob] = useState(null);
  const [session, setSession] = useState(null);
  const [error, setError] = useState(null);

  async function start() {
    setPhase("loading");
    setError(null);
    try {
      const { questions: qs } = await fetchConversationQuestions(category, 3);
      setQuestions(qs);
      setAnswers([]);
      setIndex(0);
      setCurrentBlob(null);
      setPhase("answering");
    } catch (e) {
      setError(e.message);
      setPhase("error");
    }
  }

  async function finishAnswer() {
    if (!currentBlob) return;
    const collected = [...answers, currentBlob];
    if (index < questions.length - 1) {
      setAnswers(collected);
      setIndex(index + 1);
      setCurrentBlob(null);
      return;
    }
    // last answer → analyze the whole conversation
    setPhase("finalizing");
    try {
      const s = loadSettings();
      const result = await analyzeConversation(collected, {
        category,
        questions,
        coaching: s.coachingEnabled,
        keepRecording: s.keepRecordings,
        coachingTarget: s.coachingTarget,
        coachingTone: s.coachingTone,
        coachingDepth: s.coachingDepth,
      });
      setSession(result);
      setPhase("done");
    } catch (e) {
      setError(e.message);
      setPhase("error");
    }
  }

  function reset() {
    setPhase("setup");
    setQuestions([]);
    setAnswers([]);
    setIndex(0);
    setCurrentBlob(null);
    setSession(null);
    setError(null);
  }

  if (phase === "setup") {
    return (
      <div className="card">
        <h3>Conversation drill</h3>
        <p className="settings-note">
          The interviewer asks a short series of questions on your theme. Answer
          each out loud, hit "Finished responding" to move on, and get one
          analysis of the whole exchange at the end.
        </p>
        <div className="cmp-pickers">
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <button className="primary-btn" onClick={start}>
            Start conversation
          </button>
        </div>
      </div>
    );
  }

  if (phase === "loading") return <p className="status">Preparing questions…</p>;
  if (phase === "error") {
    return (
      <div className="card">
        <p className="error">{error}</p>
        <button className="ghost-btn" onClick={reset}>Start over</button>
      </div>
    );
  }

  if (phase === "finalizing") {
    return (
      <div className="card">
        <h3>Thank you! 🎤</h3>
        <p className="status">Analyzing your conversation…</p>
      </div>
    );
  }

  if (phase === "done" && session) {
    return (
      <>
        <Results key={session.id} session={session} />
        <div className="practice-actions">
          <button className="primary-btn" onClick={reset}>
            ↻ New conversation
          </button>
        </div>
      </>
    );
  }

  // answering
  const stage = STAGES[index] || `Question ${index + 1}`;
  return (
    <div className="card conversation">
      <div className="convo-progress">
        Question {index + 1} of {questions.length} · {stage}
      </div>
      <p className="convo-question">{questions[index]}</p>
      <Recorder key={index} onRecorded={setCurrentBlob} />
      <button
        className="primary-btn"
        onClick={finishAnswer}
        disabled={!currentBlob}
        title={currentBlob ? "" : "Record your answer first"}
      >
        {index < questions.length - 1 ? "Finished responding →" : "Finish & analyze"}
      </button>
    </div>
  );
}
