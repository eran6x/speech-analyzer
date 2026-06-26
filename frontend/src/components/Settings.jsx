import { useEffect, useState } from "react";
import {
  deleteAllSessions,
  deleteRecordings,
  deleteVoice,
  enrollVoice,
  fetchProfiles,
  getVoice,
} from "../api.js";
import { loadSettings, saveSettings } from "../settings.js";
import Recorder from "./Recorder.jsx";

export default function Settings() {
  const [settings, setSettings] = useState(loadSettings);
  const [saved, setSaved] = useState(false);
  const [deleteMsg, setDeleteMsg] = useState(null);
  const [voiceEnrolled, setVoiceEnrolled] = useState(false);
  const [voiceMsg, setVoiceMsg] = useState(null);
  const [enrolling, setEnrolling] = useState(false);
  const [profiles, setProfiles] = useState([]);

  useEffect(() => {
    getVoice().then((v) => setVoiceEnrolled(v.enrolled)).catch(() => {});
    fetchProfiles().then(setProfiles).catch(() => {});
  }, []);

  const speakers = profiles.filter((p) => p.kind === "speaker");
  const styles = profiles.filter((p) => p.kind === "style");

  async function handleEnroll(blob) {
    setEnrolling(true);
    setVoiceMsg(null);
    try {
      await enrollVoice(blob);
      setVoiceEnrolled(true);
      setVoiceMsg("Voice enrolled ✓");
    } catch (e) {
      setVoiceMsg(e.message);
    } finally {
      setEnrolling(false);
    }
  }

  async function removeVoice() {
    try {
      await deleteVoice();
      setVoiceEnrolled(false);
      setVoiceMsg("Voice sample deleted.");
    } catch (e) {
      setVoiceMsg(e.message);
    }
  }

  function update(key, value) {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  function persist() {
    saveSettings(settings);
    setSaved(true);
  }

  async function handleDeleteRecordings() {
    if (!window.confirm("Delete all stored audio recordings? Your sessions, scores, and transcripts are kept.")) {
      return;
    }
    try {
      const { deleted_files } = await deleteRecordings();
      setDeleteMsg(`Deleted ${deleted_files} recording file${deleted_files === 1 ? "" : "s"}; session data kept.`);
    } catch (e) {
      setDeleteMsg(e.message);
    }
  }

  async function handleDeleteAll() {
    if (!window.confirm("Delete ALL data — every session, score, transcript, and recording? This cannot be undone.")) {
      return;
    }
    try {
      const { deleted } = await deleteAllSessions();
      setDeleteMsg(`Deleted all data (${deleted} session${deleted === 1 ? "" : "s"}).`);
    } catch (e) {
      setDeleteMsg(e.message);
    }
  }

  return (
    <div className="settings">
      <Section title="Account">
        <Field label="Display name">
          <input
            type="text"
            value={settings.displayName}
            placeholder="How should we greet you?"
            onChange={(e) => update("displayName", e.target.value)}
          />
        </Field>
        <Field label="Email">
          <input
            type="email"
            value={settings.email}
            placeholder="you@example.com"
            onChange={(e) => update("email", e.target.value)}
          />
        </Field>
      </Section>

      <Section title="Coaching">
        <p className="settings-note">
          Steer what coaching optimizes for. Picking a speaker or style also
          scores you against that target's bands ("scored vs …").
        </p>
        <Field label="Target">
          <select
            value={settings.coachingTarget}
            onChange={(e) => update("coachingTarget", e.target.value)}
          >
            <option value="">Balanced (default)</option>
            {styles.length > 0 && (
              <optgroup label="Styles">
                {styles.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </optgroup>
            )}
            {speakers.length > 0 && (
              <optgroup label="Speakers">
                {speakers.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </optgroup>
            )}
          </select>
        </Field>
        <Field label="Tone">
          <select
            value={settings.coachingTone}
            onChange={(e) => update("coachingTone", e.target.value)}
          >
            <option value="">Balanced</option>
            <option value="encouraging">Encouraging</option>
            <option value="blunt">Blunt</option>
          </select>
        </Field>
        <Field label="Depth">
          <select
            value={settings.coachingDepth}
            onChange={(e) => update("coachingDepth", e.target.value)}
          >
            <option value="">Standard</option>
            <option value="brief">Brief</option>
            <option value="detailed">Detailed</option>
          </select>
        </Field>
      </Section>

      <Section title="Voice generation">
        <p className="settings-note">
          Which engine produces the "ideal delivery" audio. <strong>Local</strong>{" "}
          and <strong>ElevenLabs</strong> clone your enrolled voice;{" "}
          <strong>OpenAI</strong> uses a preset voice (not your own) but follows
          the delivery style. Leave on Default to use the server's configured
          provider.
        </p>
        <Field label="Provider">
          <select
            value={settings.ttsProvider}
            onChange={(e) => update("ttsProvider", e.target.value)}
          >
            <option value="">Default (server)</option>
            <option value="local">Local (XTTS, your voice)</option>
            <option value="elevenlabs">ElevenLabs (your voice)</option>
            <option value="openai">OpenAI (preset voice)</option>
          </select>
        </Field>
        <Field label="Model">
          <input
            type="text"
            value={settings.ttsModel}
            placeholder="provider default (e.g. gpt-4o-mini-tts)"
            onChange={(e) => update("ttsModel", e.target.value)}
          />
        </Field>
        <Field label="Voice">
          <input
            type="text"
            value={settings.ttsVoice}
            placeholder="OpenAI: alloy/onyx/nova… · ElevenLabs: voice id"
            onChange={(e) => update("ttsVoice", e.target.value)}
          />
        </Field>
      </Section>

      <Section title="Voice">
        <p className="settings-note">
          Record a short, clean ~15s sample (read any neutral passage). It clones
          your voice for the "ideal delivery" examples and stays on this machine.
          If you don't enroll, each session's own recording is used instead.
        </p>
        <Field label="Enrollment">
          <span className="settings-hint">
            {voiceEnrolled ? "Enrolled ✓" : "Not enrolled"}
          </span>
          {voiceEnrolled && (
            <button className="ghost-btn" onClick={removeVoice}>
              Delete
            </button>
          )}
        </Field>
        <Recorder onRecorded={handleEnroll} disabled={enrolling} />
        {voiceMsg && <p className="settings-hint">{voiceMsg}</p>}
      </Section>

      <Section title="Privacy">
        <Toggle
          label="Keep recordings after analysis"
          hint="Audio is stored locally in backend/recordings/. Turn off to discard after scoring."
          checked={settings.keepRecordings}
          onChange={(v) => update("keepRecordings", v)}
        />
        <Field label="Recordings only">
          <button className="ghost-btn" onClick={handleDeleteRecordings}>
            Delete recordings
          </button>
        </Field>
        <Field label="Everything">
          <button className="ghost-btn danger" onClick={handleDeleteAll}>
            Delete all data
          </button>
        </Field>
        {deleteMsg && <p className="settings-hint">{deleteMsg}</p>}
      </Section>

      <Section title="Security">
        <p className="settings-note">
          Everything runs locally — the backend, the SQLite database, and your
          recordings never leave your machine. The Anthropic API key used for
          coaching is read from <code>backend/.env</code> and is never sent to
          the browser.
        </p>
        <Field label="Lock with a passcode">
          <button className="ghost-btn" disabled>
            Set passcode
          </button>
          <Soon />
        </Field>
      </Section>

      <Section title="General">
        <Toggle
          label="AI coaching feedback"
          hint="Show Claude-generated coaching after each session."
          checked={settings.coachingEnabled}
          onChange={(v) => update("coachingEnabled", v)}
        />
        <Field label="Target pace (wpm)">
          <input
            type="number"
            min="80"
            max="220"
            value={settings.targetPaceWpm}
            onChange={(e) => update("targetPaceWpm", Number(e.target.value))}
          />
        </Field>
        <Field label="Daily practice reminder">
          <button className="ghost-btn" disabled>
            Enable reminders
          </button>
          <Soon />
        </Field>
      </Section>

      <button className="primary-btn" onClick={persist}>
        {saved ? "Saved ✓" : "Save settings"}
      </button>
      <p className="settings-note">
        Settings are stored in your browser. <strong>Keep recordings</strong>,{" "}
        <strong>AI coaching feedback</strong>, and <strong>Delete all
        sessions</strong> take effect now; the rest are placeholders for a future
        update.
      </p>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="card settings-section">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div className="settings-field">
      <label>{label}</label>
      <div className="settings-control">{children}</div>
    </div>
  );
}

function Toggle({ label, hint, checked, onChange }) {
  return (
    <div className="settings-field">
      <label>
        {label}
        {hint && <span className="settings-hint">{hint}</span>}
      </label>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
    </div>
  );
}

function Soon() {
  return <span className="soon">coming soon</span>;
}
