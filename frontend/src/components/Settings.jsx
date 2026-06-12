import { useState } from "react";
import { deleteAllSessions } from "../api.js";
import { loadSettings, saveSettings } from "../settings.js";

export default function Settings() {
  const [settings, setSettings] = useState(loadSettings);
  const [saved, setSaved] = useState(false);
  const [deleteMsg, setDeleteMsg] = useState(null);

  function update(key, value) {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  function persist() {
    saveSettings(settings);
    setSaved(true);
  }

  async function handleDeleteAll() {
    if (!window.confirm("Delete all sessions and recordings? This cannot be undone.")) {
      return;
    }
    try {
      const { deleted } = await deleteAllSessions();
      setDeleteMsg(`Deleted ${deleted} session${deleted === 1 ? "" : "s"}.`);
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

      <Section title="Privacy">
        <Toggle
          label="Keep recordings after analysis"
          hint="Audio is stored locally in backend/recordings/. Turn off to discard after scoring."
          checked={settings.keepRecordings}
          onChange={(v) => update("keepRecordings", v)}
        />
        <Field label="Your data">
          <button className="ghost-btn" onClick={handleDeleteAll}>
            Delete all sessions
          </button>
          {deleteMsg && <span className="settings-hint">{deleteMsg}</span>}
        </Field>
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
